"""Hardware capability detection and deterministic optimization profiles."""

from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PerformanceProfile(Enum):
    """Supported inference performance profiles."""

    BALANCED = "balanced"
    LOW_VRAM = "low_vram"
    HIGH_PERFORMANCE = "high_performance"
    CUSTOM = "custom"

    @classmethod
    def parse(cls, value: str | None) -> PerformanceProfile:
        try:
            return cls(value or cls.BALANCED.value)
        except ValueError as error:
            choices = ", ".join(item.value for item in cls)
            raise ValueError(f"Unknown performance profile: {value}. Choose: {choices}") from error


@dataclass(frozen=True)
class HardwareCapabilities:
    """Capabilities relevant to one inference device."""

    cuda_available: bool
    device_count: int = 0
    device_id: int = 0
    device_name: str = "CPU"
    total_vram_gib: float = 0.0
    bf16_supported: bool = False
    native_sdpa_available: bool = False
    xformers_available: bool = False
    torch_compile_available: bool = False


@dataclass(frozen=True)
class OptimizationPlan:
    """Resolved, non-conflicting model-loading options."""

    profile: PerformanceProfile
    precision: str
    cpu_offload: bool
    sequential_offload: bool
    vae_tiling: bool
    vae_slicing: bool
    attention_slicing: bool
    flash_attention: bool
    xformers: bool
    torch_compile: bool
    device_id: int
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_engine_options(self) -> dict[str, Any]:
        """Return options accepted by the current engine API."""
        data = asdict(self)
        data.pop("profile")
        data.pop("warnings")
        return data


def detect_hardware_capabilities(device_id: int = 0) -> HardwareCapabilities:
    """Inspect the active PyTorch build without importing optional accelerators."""
    try:
        import torch
    except ImportError:
        return HardwareCapabilities(cuda_available=False, device_id=device_id)

    cuda_available = bool(torch.cuda.is_available())
    device_count = int(torch.cuda.device_count()) if cuda_available else 0
    valid_device = cuda_available and 0 <= device_id < device_count
    if not valid_device:
        return HardwareCapabilities(
            cuda_available=cuda_available,
            device_count=device_count,
            device_id=device_id,
            native_sdpa_available=hasattr(
                torch.nn.functional,
                "scaled_dot_product_attention",
            ),
            xformers_available=importlib.util.find_spec("xformers") is not None,
            torch_compile_available=hasattr(torch, "compile"),
        )

    properties = torch.cuda.get_device_properties(device_id)
    return HardwareCapabilities(
        cuda_available=True,
        device_count=device_count,
        device_id=device_id,
        device_name=torch.cuda.get_device_name(device_id),
        total_vram_gib=properties.total_memory / 1024**3,
        bf16_supported=bool(torch.cuda.is_bf16_supported()),
        native_sdpa_available=hasattr(
            torch.nn.functional,
            "scaled_dot_product_attention",
        ),
        xformers_available=importlib.util.find_spec("xformers") is not None,
        torch_compile_available=hasattr(torch, "compile"),
    )


def _custom_bool(options: dict[str, Any], key: str, default: bool) -> bool:
    return bool(options.get(key, default))


def build_optimization_plan(
    profile: PerformanceProfile,
    capabilities: HardwareCapabilities,
    model_vram_required_gib: float,
    configured_options: dict[str, Any] | None = None,
) -> OptimizationPlan:
    """Resolve a profile into a safe, deterministic engine plan."""
    options = dict(configured_options or {})
    warnings: list[str] = []
    precision = str(options.get("precision", "auto"))
    if precision == "auto":
        precision = "bf16" if capabilities.bf16_supported else "fp16"
    if precision not in {"fp16", "bf16", "fp32"}:
        raise ValueError(f"Unsupported precision: {precision}")
    if precision == "bf16" and not capabilities.bf16_supported:
        warnings.append("BF16 is unavailable; using FP16")
        precision = "fp16"

    if profile is PerformanceProfile.LOW_VRAM:
        cpu_offload = False
        sequential_offload = True
        vae_tiling = True
        vae_slicing = True
        attention_slicing = True
        flash_attention = capabilities.native_sdpa_available
        xformers = False
        torch_compile = False
    elif profile is PerformanceProfile.HIGH_PERFORMANCE:
        if (
            capabilities.cuda_available
            and model_vram_required_gib > 0
            and capabilities.total_vram_gib < model_vram_required_gib
        ):
            raise ValueError(
                "High-performance mode requires at least "
                f"{model_vram_required_gib:.1f} GiB VRAM; "
                f"detected {capabilities.total_vram_gib:.1f} GiB"
            )
        cpu_offload = False
        sequential_offload = False
        vae_tiling = False
        vae_slicing = False
        attention_slicing = False
        flash_attention = capabilities.native_sdpa_available
        xformers = capabilities.xformers_available
        torch_compile = capabilities.torch_compile_available
    elif profile is PerformanceProfile.CUSTOM:
        cpu_offload = _custom_bool(options, "cpu_offload", False)
        sequential_offload = _custom_bool(options, "sequential_offload", False)
        if cpu_offload and sequential_offload:
            raise ValueError("cpu_offload and sequential_offload are mutually exclusive")
        vae_tiling = _custom_bool(options, "vae_tiling", True)
        vae_slicing = _custom_bool(options, "vae_slicing", True)
        attention_slicing = _custom_bool(options, "attention_slicing", False)
        flash_attention = _custom_bool(options, "flash_attention", True)
        xformers = _custom_bool(options, "xformers", False)
        torch_compile = _custom_bool(options, "torch_compile", False)
    else:
        cpu_offload = False
        sequential_offload = False
        vae_tiling = True
        vae_slicing = True
        attention_slicing = False
        flash_attention = capabilities.native_sdpa_available
        xformers = False
        torch_compile = False
        if capabilities.cuda_available and model_vram_required_gib > 0:
            ratio = capabilities.total_vram_gib / model_vram_required_gib
            if ratio < 0.75:
                sequential_offload = True
                attention_slicing = True
                warnings.append("VRAM is far below the model requirement; using sequential offload")
            elif capabilities.total_vram_gib < model_vram_required_gib + 1.0:
                cpu_offload = True
                warnings.append("VRAM headroom is limited; using model CPU offload")

    if flash_attention and not capabilities.native_sdpa_available:
        warnings.append("Flash/native SDPA is unavailable and was disabled")
        flash_attention = False
    if xformers and not capabilities.xformers_available:
        warnings.append("xFormers is not installed and was disabled")
        xformers = False
    if torch_compile and not capabilities.torch_compile_available:
        warnings.append("torch.compile is unavailable and was disabled")
        torch_compile = False
    if not capabilities.cuda_available:
        warnings.append("CUDA is unavailable in the installed PyTorch build")

    return OptimizationPlan(
        profile=profile,
        precision=precision,
        cpu_offload=cpu_offload,
        sequential_offload=sequential_offload,
        vae_tiling=vae_tiling,
        vae_slicing=vae_slicing,
        attention_slicing=attention_slicing,
        flash_attention=flash_attention,
        xformers=xformers,
        torch_compile=torch_compile,
        device_id=capabilities.device_id,
        warnings=tuple(warnings),
    )
