"""Structured inference error classification and safe CUDA OOM recovery."""

from __future__ import annotations

import gc
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from utils.logger import get_logger

logger = get_logger("inference_errors")
_MIB = 1024**2


class InferenceErrorKind(Enum):
    """Stable error categories exposed to tasks, history, UI, and logs."""

    CANCELLED = "cancelled"
    CUDA_OOM = "cuda_oom"
    CUDA_UNAVAILABLE = "cuda_unavailable"
    DEPENDENCY = "dependency"
    VALIDATION = "validation"
    FILE_SYSTEM = "file_system"
    MODEL_LOAD = "model_load"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CudaMemorySnapshot:
    """Best-effort CUDA allocator and device-memory snapshot in MiB."""

    device_id: int
    allocated_mib: int = 0
    reserved_mib: int = 0
    peak_allocated_mib: int = 0
    free_mib: int = 0
    total_mib: int = 0


@dataclass(frozen=True)
class InferenceErrorReport:
    """Serializable error report with a user-safe message and diagnostics."""

    kind: InferenceErrorKind
    phase: str
    user_message: str
    technical_message: str
    recoverable: bool
    memory: CudaMemorySnapshot | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InferenceErrorReport:
        memory_data = data.get("memory")
        memory = CudaMemorySnapshot(**memory_data) if isinstance(memory_data, dict) else None
        kind_value = str(data.get("kind", InferenceErrorKind.UNKNOWN.value))
        try:
            kind = InferenceErrorKind(kind_value)
        except ValueError:
            kind = InferenceErrorKind.UNKNOWN
        details = data.get("details", {})
        return cls(
            kind=kind,
            phase=str(data.get("phase", "inference")),
            user_message=str(data.get("user_message", "推理失败")),
            technical_message=str(data.get("technical_message", "")),
            recoverable=bool(data.get("recoverable", False)),
            memory=memory,
            details=dict(details) if isinstance(details, dict) else {},
        )


class InferenceRuntimeError(RuntimeError):
    """Runtime exception carrying a structured inference error report."""

    def __init__(self, report: InferenceErrorReport):
        super().__init__(report.user_message)
        self.report = report


def capture_cuda_memory(device_id: int = 0) -> CudaMemorySnapshot | None:
    """Capture CUDA memory metrics without failing the original operation."""
    try:
        import torch

        if not torch.cuda.is_available() or not 0 <= device_id < torch.cuda.device_count():
            return None
        free_bytes, total_bytes = torch.cuda.mem_get_info(device_id)
        return CudaMemorySnapshot(
            device_id=device_id,
            allocated_mib=int(torch.cuda.memory_allocated(device_id) / _MIB),
            reserved_mib=int(torch.cuda.memory_reserved(device_id) / _MIB),
            peak_allocated_mib=int(torch.cuda.max_memory_allocated(device_id) / _MIB),
            free_mib=int(free_bytes / _MIB),
            total_mib=int(total_bytes / _MIB),
        )
    except Exception:
        logger.debug("Unable to capture CUDA memory snapshot", exc_info=True)
        return None


def recover_cuda_memory(device_id: int = 0) -> bool:
    """Best-effort allocator cleanup after OOM; never masks the original error."""
    gc.collect()
    try:
        import torch

        if not torch.cuda.is_available() or not 0 <= device_id < torch.cuda.device_count():
            return False
        with torch.cuda.device(device_id):
            torch.cuda.empty_cache()
            if hasattr(torch.cuda, "ipc_collect"):
                torch.cuda.ipc_collect()
            if hasattr(torch.cuda, "reset_peak_memory_stats"):
                torch.cuda.reset_peak_memory_stats(device_id)
        return True
    except Exception:
        logger.warning("CUDA memory cleanup failed", exc_info=True)
        return False


def _is_cuda_oom(error: BaseException) -> bool:
    try:
        import torch

        if isinstance(error, torch.OutOfMemoryError):
            return True
    except (ImportError, AttributeError):
        pass
    message = str(error).lower()
    return "cuda out of memory" in message or "cuda error: out of memory" in message


def classify_inference_error(
    error: BaseException,
    *,
    phase: str,
    device_id: int = 0,
    cleanup_oom: bool = True,
) -> InferenceErrorReport:
    """Classify an exception and perform safe OOM cleanup when applicable."""
    technical_message = str(error) or error.__class__.__name__
    class_name = error.__class__.__name__

    if class_name == "GenerationCancelledError":
        return InferenceErrorReport(
            kind=InferenceErrorKind.CANCELLED,
            phase=phase,
            user_message="任务已取消",
            technical_message=technical_message,
            recoverable=True,
        )

    if _is_cuda_oom(error):
        memory = capture_cuda_memory(device_id)
        cleanup_succeeded = recover_cuda_memory(device_id) if cleanup_oom else False
        memory_hint = ""
        if memory:
            memory_hint = (
                f"（已分配 {memory.allocated_mib} MiB，保留 {memory.reserved_mib} MiB，"
                f"可用 {memory.free_mib} MiB）"
            )
        return InferenceErrorReport(
            kind=InferenceErrorKind.CUDA_OOM,
            phase=phase,
            user_message=(
                "GPU 显存不足，已尝试清理缓存。请使用低显存档位、降低分辨率/帧数，"
                f"或卸载 LoRA 后重试。{memory_hint}"
            ),
            technical_message=technical_message,
            recoverable=True,
            memory=memory,
            details={"cleanup_succeeded": cleanup_succeeded},
        )

    message_lower = technical_message.lower()
    if "cuda" in message_lower and (
        "not available" in message_lower
        or "does not support cuda" in message_lower
        or "cuda build" in message_lower
    ):
        kind = InferenceErrorKind.CUDA_UNAVAILABLE
        user_message = "当前 PyTorch 无法使用 CUDA，请安装匹配的 CUDA 版 PyTorch。"
        recoverable = False
    elif isinstance(error, (ImportError, ModuleNotFoundError)):
        kind = InferenceErrorKind.DEPENDENCY
        user_message = f"缺少运行依赖：{technical_message}"
        recoverable = False
    elif isinstance(error, (ValueError, TypeError)):
        kind = InferenceErrorKind.VALIDATION
        user_message = technical_message
        recoverable = True
    elif isinstance(error, (FileNotFoundError, PermissionError, OSError)):
        kind = InferenceErrorKind.FILE_SYSTEM
        user_message = f"文件或目录操作失败：{technical_message}"
        recoverable = True
    elif phase == "model_load":
        kind = InferenceErrorKind.MODEL_LOAD
        user_message = f"模型加载失败：{technical_message}"
        recoverable = True
    elif isinstance(error, RuntimeError):
        kind = InferenceErrorKind.RUNTIME
        user_message = technical_message
        recoverable = True
    else:
        kind = InferenceErrorKind.UNKNOWN
        user_message = f"推理失败：{technical_message}"
        recoverable = False

    return InferenceErrorReport(
        kind=kind,
        phase=phase,
        user_message=user_message,
        technical_message=technical_message,
        recoverable=recoverable,
    )
