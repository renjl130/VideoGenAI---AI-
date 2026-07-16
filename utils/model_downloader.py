"""Thread-safe, resumable local model-download management."""

from __future__ import annotations

import json
import os
import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import ClassVar

try:
    from huggingface_hub import snapshot_download

    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

try:
    from modelscope import snapshot_download as ms_snapshot_download

    MODELSCOPE_AVAILABLE = True
except ImportError:
    MODELSCOPE_AVAILABLE = False

from utils.logger import get_logger
from utils.paths import APP_PATHS, resolve_project_path

logger = get_logger("model_downloader")


@dataclass(frozen=True)
class ModelInfo:
    """Static metadata for one model supported by an engine."""

    model_id: str
    model_type: str
    model_size: str
    resolution: str
    repo_id: str
    description: str
    license: str
    vram_required: int
    download_size: float
    engine: str = "wan"
    implemented: bool = True


class ModelStatus(Enum):
    """Local model availability state."""

    NOT_DOWNLOADED = "not_downloaded"
    INCOMPLETE = "incomplete"
    READY = "ready"
    UNSUPPORTED = "unsupported"


# These are rounded on-disk sizes of the complete official Diffusers repositories,
# not just the video transformer weights. Accurate values prevent a misleading
# ``5 GB`` first-download prompt for a roughly 27 GiB model package.
SUPPORTED_MODELS: dict[str, ModelInfo] = {
    "wan2.1-t2v-1.3b": ModelInfo(
        model_id="wan2.1-t2v-1.3b",
        model_type="t2v",
        model_size="1.3b",
        resolution="480p",
        repo_id="Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        description="Wan2.1 文生视频 1.3B，适合消费级 GPU",
        license="Apache-2.0",
        vram_required=8,
        download_size=27.0,
    ),
    "wan2.1-t2v-14b": ModelInfo(
        model_id="wan2.1-t2v-14b",
        model_type="t2v",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-T2V-14B-Diffusers",
        description="Wan2.1 文生视频 14B，高质量生成",
        license="Apache-2.0",
        vram_required=24,
        download_size=75.0,
    ),
    "wan2.1-i2v-14b-720p": ModelInfo(
        model_id="wan2.1-i2v-14b-720p",
        model_type="i2v",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-I2V-14B-720P-Diffusers",
        description="Wan2.1 图生视频 14B，支持 720P",
        license="Apache-2.0",
        vram_required=24,
        download_size=84.0,
    ),
    "wan2.1-i2v-14b-480p": ModelInfo(
        model_id="wan2.1-i2v-14b-480p",
        model_type="i2v",
        model_size="14b",
        resolution="480p",
        repo_id="Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
        description="Wan2.1 图生视频 14B，支持 480P",
        license="Apache-2.0",
        vram_required=16,
        download_size=84.0,
    ),
    "wan2.1-flf2v-14b": ModelInfo(
        model_id="wan2.1-flf2v-14b",
        model_type="flf2v",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-FLF2V-14B-720P",
        description="Wan2.1 首尾帧视频生成 14B（当前未实现）",
        license="Apache-2.0",
        vram_required=24,
        download_size=84.0,
        implemented=False,
    ),
    "wan2.1-vace-1.3b": ModelInfo(
        model_id="wan2.1-vace-1.3b",
        model_type="vace",
        model_size="1.3b",
        resolution="480p",
        repo_id="Wan-AI/Wan2.1-VACE-1.3B",
        description="Wan2.1 VACE 视频编辑 1.3B（当前未实现）",
        license="Apache-2.0",
        vram_required=8,
        download_size=27.0,
        implemented=False,
    ),
    "wan2.1-vace-14b": ModelInfo(
        model_id="wan2.1-vace-14b",
        model_type="vace",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-VACE-14B",
        description="Wan2.1 VACE 视频编辑 14B（当前未实现）",
        license="Apache-2.0",
        vram_required=24,
        download_size=84.0,
        implemented=False,
    ),
    "cogvideox-2b": ModelInfo(
        model_id="cogvideox-2b",
        model_type="t2v",
        model_size="2b",
        resolution="480p",
        repo_id="THUDM/CogVideoX-2b",
        engine="cogvideox",
        description="CogVideoX 2B 文生视频（当前未实现）",
        license="Apache-2.0",
        vram_required=4,
        download_size=8.0,
        implemented=False,
    ),
    "cogvideox-5b": ModelInfo(
        model_id="cogvideox-5b",
        model_type="t2v",
        model_size="5b",
        resolution="720p",
        repo_id="THUDM/CogVideoX-5b",
        engine="cogvideox",
        description="CogVideoX 5B 文生视频（当前未实现）",
        license="CogVideoX LICENSE",
        vram_required=10,
        download_size=15.0,
        implemented=False,
    ),
}


class DownloadProgress:
    """A lock-protected, copyable snapshot of a model download."""

    def __init__(self, model_id: str, total_size: int):
        self.model_id = model_id
        self.total_size = total_size
        self.downloaded_size = 0
        self.status = "pending"
        self.error: str | None = None
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self._lock = threading.RLock()

    @property
    def progress(self) -> float:
        """Return current progress as a bounded percentage."""
        with self._lock:
            if self.total_size <= 0:
                return 0.0
            return min(100.0, (self.downloaded_size / self.total_size) * 100)

    @property
    def speed(self) -> float:
        """Return average on-disk write speed in MiB/s."""
        with self._lock:
            if not self.start_time or self.downloaded_size <= 0:
                return 0.0
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed <= 0:
                return 0.0
            return self.downloaded_size / 1024 / 1024 / elapsed

    @property
    def eta(self) -> int:
        """Return estimated remaining seconds, or zero while unavailable."""
        speed = self.speed
        with self._lock:
            if speed <= 0:
                return 0
            remaining = max(0, self.total_size - self.downloaded_size)
        return int(remaining / 1024 / 1024 / speed)

    def update_downloaded_size(self, downloaded_size: int) -> None:
        """Record observed bytes without allowing a negative value."""
        with self._lock:
            self.downloaded_size = max(0, downloaded_size)

    def set_state(
        self,
        status: str,
        *,
        error: str | None = None,
        completed: bool = False,
    ) -> None:
        """Atomically update lifecycle fields."""
        with self._lock:
            self.status = status
            self.error = error
            if completed:
                self.end_time = datetime.now()

    def snapshot(self) -> DownloadProgress:
        """Return a detached value so callers cannot race manager updates."""
        with self._lock:
            result = DownloadProgress(self.model_id, self.total_size)
            result.downloaded_size = self.downloaded_size
            result.status = self.status
            result.error = self.error
            result.start_time = self.start_time
            result.end_time = self.end_time
            return result


DownloadCallback = Callable[[str, DownloadProgress], None]


class ModelDownloader:
    """Manage safe, resumable downloads into the configured models directory."""

    _instance: ClassVar[ModelDownloader | None] = None
    _initialized: bool

    def __new__(cls, models_dir: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, models_dir: str | None = None):
        if self._initialized:
            return

        self._initialized = True
        self._models_dir = resolve_project_path(models_dir) if models_dir else APP_PATHS.models
        self._models_dir.mkdir(parents=True, exist_ok=True)
        self._downloads: dict[str, DownloadProgress] = {}
        self._callbacks: list[DownloadCallback] = []
        self._download_callbacks: dict[str, list[DownloadCallback]] = {}
        self._download_threads: dict[str, threading.Thread] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._model_statuses: dict[str, ModelStatus] = {}
        self._downloaded_models: dict[str, ModelInfo] = {}
        self._lock = threading.RLock()
        self._mirrors: dict[str, str | None] = {
            "huggingface": None,
            "hf-mirror": "https://hf-mirror.com",
            "modelscope": "modelscope",
        }
        self._current_mirror = "huggingface"
        self._scan_downloaded_models()

    def _scan_downloaded_models(self) -> None:
        """Scan and validate the on-disk model registry."""
        downloaded_models: dict[str, ModelInfo] = {}
        model_statuses: dict[str, ModelStatus] = {}
        for model_id, model_info in SUPPORTED_MODELS.items():
            model_path = self._models_dir / model_id
            status = self._inspect_model_path(model_path, model_info)
            model_statuses[model_id] = status
            if status is ModelStatus.READY:
                downloaded_models[model_id] = model_info
        with self._lock:
            self._downloaded_models = downloaded_models
            self._model_statuses = model_statuses

    @staticmethod
    def _has_nonempty_file(path: Path) -> bool:
        try:
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False

    @classmethod
    def _has_weight_artifact(cls, directory: Path, stem: str) -> bool:
        """Validate direct weights or every shard referenced by a Diffusers index."""
        for extension in ("safetensors", "bin"):
            direct = directory / f"{stem}.{extension}"
            if cls._has_nonempty_file(direct):
                return True

            index_path = directory / f"{stem}.{extension}.index.json"
            if not cls._has_nonempty_file(index_path):
                continue
            try:
                index_data = json.loads(index_path.read_text(encoding="utf-8"))
                weight_map = index_data.get("weight_map", {})
                shard_names = set(weight_map.values()) if isinstance(weight_map, dict) else set()
            except (OSError, ValueError, TypeError):
                continue
            if shard_names and all(
                isinstance(name, str) and cls._has_nonempty_file(directory / name)
                for name in shard_names
            ):
                return True
        return False

    @classmethod
    def _inspect_model_path(cls, model_path: Path, model_info: ModelInfo) -> ModelStatus:
        """Validate the minimum loadable Diffusers layout and real weights."""
        if not model_info.implemented:
            return ModelStatus.UNSUPPORTED
        if not model_path.is_dir():
            return ModelStatus.NOT_DOWNLOADED

        try:
            if not any(model_path.iterdir()):
                return ModelStatus.NOT_DOWNLOADED
            download_cache = model_path / ".cache" / "huggingface" / "download"
            if download_cache.exists() and any(download_cache.rglob("*.incomplete")):
                return ModelStatus.INCOMPLETE
        except OSError:
            return ModelStatus.INCOMPLETE

        required_files = (
            model_path / "model_index.json",
            model_path / "scheduler" / "scheduler_config.json",
            model_path / "text_encoder" / "config.json",
            model_path / "tokenizer" / "tokenizer_config.json",
            model_path / "tokenizer" / "tokenizer.json",
            model_path / "transformer" / "config.json",
            model_path / "vae" / "config.json",
        )
        if not all(cls._has_nonempty_file(path) for path in required_files):
            return ModelStatus.INCOMPLETE

        if not cls._has_weight_artifact(model_path / "text_encoder", "model"):
            return ModelStatus.INCOMPLETE
        if not cls._has_weight_artifact(model_path / "transformer", "diffusion_pytorch_model"):
            return ModelStatus.INCOMPLETE
        if not cls._has_weight_artifact(model_path / "vae", "diffusion_pytorch_model"):
            return ModelStatus.INCOMPLETE

        if model_info.model_type == "i2v":
            image_encoder = model_path / "image_encoder"
            if not cls._has_nonempty_file(image_encoder / "config.json"):
                return ModelStatus.INCOMPLETE
            if not cls._has_weight_artifact(image_encoder, "model"):
                return ModelStatus.INCOMPLETE
        return ModelStatus.READY

    def refresh(self) -> None:
        """Refresh local availability, retaining active download state."""
        self._scan_downloaded_models()
        with self._lock:
            for model_id, thread in self._download_threads.items():
                if thread.is_alive():
                    self._model_statuses[model_id] = ModelStatus.INCOMPLETE
                    self._downloaded_models.pop(model_id, None)

    def get_downloaded_models(self) -> dict[str, ModelInfo]:
        with self._lock:
            return self._downloaded_models.copy()

    def get_incomplete_models(self) -> dict[str, ModelInfo]:
        with self._lock:
            return {
                model_id: SUPPORTED_MODELS[model_id]
                for model_id, status in self._model_statuses.items()
                if status is ModelStatus.INCOMPLETE
            }

    def get_model_status(self, model_id: str) -> ModelStatus:
        with self._lock:
            return self._model_statuses.get(model_id, ModelStatus.NOT_DOWNLOADED)

    def get_available_models(self) -> dict[str, ModelInfo]:
        return SUPPORTED_MODELS.copy()

    def is_model_downloaded(self, model_id: str) -> bool:
        return self.get_model_status(model_id) is ModelStatus.READY

    def get_model_path(self, model_id: str) -> Path | None:
        if self.is_model_downloaded(model_id):
            return self._models_dir / model_id
        return None

    def set_mirror(self, mirror: str) -> bool:
        """Set a supported download source without leaking global HF environment state."""
        if mirror not in self._mirrors:
            logger.error("不支持的模型镜像: %s", mirror)
            return False
        with self._lock:
            self._current_mirror = mirror
        logger.info("已切换模型镜像: %s", mirror)
        return True

    def download_model(self, model_id: str, callback: DownloadCallback | None = None) -> bool:
        """Start a background download; an incomplete directory is resumed by HF Hub."""
        model_info = SUPPORTED_MODELS.get(model_id)
        if model_info is None:
            logger.error("未知模型: %s", model_id)
            return False
        if not model_info.implemented:
            logger.error("当前版本尚未实现该模型: %s", model_id)
            return False
        if self.is_model_downloaded(model_id):
            logger.info("模型已完整下载: %s", model_id)
            return True

        with self._lock:
            existing_thread = self._download_threads.get(model_id)
            if existing_thread and existing_thread.is_alive():
                logger.warning("模型下载已在进行: %s", model_id)
                return False
            total_size = int(model_info.download_size * 1024**3)
            progress = DownloadProgress(model_id, total_size)
            progress.start_time = datetime.now()
            progress.set_state("downloading")
            self._downloads[model_id] = progress
            if callback is not None:
                self._download_callbacks.setdefault(model_id, []).append(callback)
            self._cancel_events[model_id] = threading.Event()
            self._model_statuses[model_id] = ModelStatus.INCOMPLETE
            thread = threading.Thread(
                target=self._download_thread,
                args=(model_id, model_info),
                name=f"model-download-{model_id}",
                daemon=True,
            )
            self._download_threads[model_id] = thread
            thread.start()
        self._notify_callbacks(model_id, progress)
        return True

    def _download_thread(self, model_id: str, model_info: ModelInfo) -> None:
        progress = self._downloads[model_id]
        cancel_event = self._cancel_events[model_id]
        monitor_stop = threading.Event()
        monitor = threading.Thread(
            target=self._monitor_download_progress,
            args=(model_id, model_info, progress, monitor_stop),
            name=f"model-download-monitor-{model_id}",
            daemon=True,
        )
        monitor.start()

        try:
            model_path = self._models_dir / model_id
            if cancel_event.is_set():
                self._mark_cancelled(model_id, progress)
                return
            if self._current_mirror == "modelscope":
                self._download_from_modelscope(model_info.repo_id, str(model_path))
            else:
                self._download_from_huggingface(model_info.repo_id, str(model_path))
            if cancel_event.is_set():
                self._mark_cancelled(model_id, progress)
                return

            status = self._inspect_model_path(model_path, model_info)
            if status is not ModelStatus.READY:
                raise RuntimeError("下载结束，但模型文件完整性校验失败")
            progress.update_downloaded_size(progress.total_size)
            progress.set_state("completed", completed=True)
            with self._lock:
                self._downloaded_models[model_id] = model_info
                self._model_statuses[model_id] = ModelStatus.READY
            logger.info("模型下载并校验完成: %s", model_id)
        except Exception as error:
            if cancel_event.is_set():
                self._mark_cancelled(model_id, progress)
            else:
                progress.set_state("failed", error=str(error), completed=True)
                with self._lock:
                    self._model_statuses[model_id] = ModelStatus.INCOMPLETE
                    self._downloaded_models.pop(model_id, None)
                logger.exception("模型下载失败: %s", model_id)
        finally:
            monitor_stop.set()
            monitor.join(timeout=2.0)
            self._refresh_progress_from_disk(model_id, model_info, progress)
            self._notify_callbacks(model_id, progress)
            with self._lock:
                self._cancel_events.pop(model_id, None)
                self._download_callbacks.pop(model_id, None)

    def _mark_cancelled(self, model_id: str, progress: DownloadProgress) -> None:
        progress.set_state("cancelled", completed=True)
        with self._lock:
            self._model_statuses[model_id] = ModelStatus.INCOMPLETE
            self._downloaded_models.pop(model_id, None)
        logger.info("模型下载已取消，保留部分文件用于续传: %s", model_id)

    def _monitor_download_progress(
        self,
        model_id: str,
        model_info: ModelInfo,
        progress: DownloadProgress,
        stop_event: threading.Event,
    ) -> None:
        """Publish real on-disk byte progress while Hub downloads in its own threads."""
        while not stop_event.wait(1.0):
            self._refresh_progress_from_disk(model_id, model_info, progress)
            self._notify_callbacks(model_id, progress)

    def _refresh_progress_from_disk(
        self,
        model_id: str,
        model_info: ModelInfo,
        progress: DownloadProgress,
    ) -> None:
        del model_info
        model_path = self._models_dir / model_id
        progress.update_downloaded_size(
            self._directory_size(model_path, cache_since=progress.start_time)
        )

    @staticmethod
    def _directory_size(
        directory: Path,
        *,
        cache_since: datetime | None = None,
    ) -> int:
        """Measure Diffusers payload and only this session's active Hub partial files.

        Hugging Face writes large artifacts into ``.cache`` before atomically moving
        them to the model layout. Counting every cache entry would make abandoned
        downloads and unrelated repository files inflate progress, so cache bytes are
        counted only for supported Diffusers component folders modified during the
        active download session.
        """
        if not directory.exists():
            return 0
        payload_roots = {
            "image_encoder",
            "model_index.json",
            "scheduler",
            "text_encoder",
            "tokenizer",
            "transformer",
            "vae",
        }
        total = 0
        try:
            for root, directories, filenames in os.walk(directory):
                root_path = Path(root)
                relative_root = root_path.relative_to(directory)
                if relative_root == Path("."):
                    directories[:] = [name for name in directories if name in payload_roots]
                    filenames = [name for name in filenames if name in payload_roots]
                else:
                    top_level = relative_root.parts[0]
                    if top_level not in payload_roots:
                        directories[:] = []
                        continue
                for filename in filenames:
                    file_path = root_path / filename
                    try:
                        total += file_path.stat().st_size
                    except OSError:
                        continue

            if cache_since is None:
                return total

            # File timestamp precision can be coarser than the session clock. Keep a
            # small grace interval so a partial created immediately after start is not
            # incorrectly omitted, while still excluding stale partial downloads.
            session_started_at = cache_since.timestamp() - 2.0
            cache_directory = directory / ".cache" / "huggingface" / "download"
            for cache_file in cache_directory.glob("*/*.incomplete"):
                if cache_file.parent.name not in payload_roots:
                    continue
                try:
                    if cache_file.stat().st_mtime >= session_started_at:
                        total += cache_file.stat().st_size
                except OSError:
                    continue
        except OSError:
            return total
        return total

    def _download_from_huggingface(self, repo_id: str, local_dir: str) -> None:
        if not HF_HUB_AVAILABLE:
            raise ImportError("缺少 huggingface_hub: pip install huggingface_hub")
        with self._lock:
            endpoint = self._mirrors[self._current_mirror]
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            etag_timeout=30,
            max_workers=4,
            endpoint=endpoint,
        )

    @staticmethod
    def _download_from_modelscope(repo_id: str, local_dir: str) -> None:
        if not MODELSCOPE_AVAILABLE:
            raise ImportError("缺少 modelscope: pip install modelscope")
        ms_snapshot_download(model_id=repo_id, local_dir=local_dir)

    def cancel_download(self, model_id: str) -> bool:
        """Request cancellation; the current file transfer may finish before Hub returns."""
        with self._lock:
            event = self._cancel_events.get(model_id)
            progress = self._downloads.get(model_id)
            thread = self._download_threads.get(model_id)
            if event is None or progress is None or thread is None or not thread.is_alive():
                return False
            event.set()
            progress.set_state("cancelling")
        self._notify_callbacks(model_id, progress)
        logger.info("已请求取消模型下载: %s", model_id)
        return True

    def delete_model(self, model_id: str) -> bool:
        """Delete a known complete or partial model without touching arbitrary paths."""
        if model_id not in SUPPORTED_MODELS:
            return False
        with self._lock:
            thread = self._download_threads.get(model_id)
            if thread and thread.is_alive():
                logger.warning("下载进行中，不能删除模型: %s", model_id)
                return False
        model_path = self._models_dir / model_id
        if not model_path.exists():
            return False
        try:
            shutil.rmtree(model_path)
        except OSError:
            logger.exception("删除模型失败: %s", model_id)
            return False
        with self._lock:
            self._downloads.pop(model_id, None)
            self._downloaded_models.pop(model_id, None)
            self._model_statuses[model_id] = ModelStatus.NOT_DOWNLOADED
        logger.info("模型已删除: %s", model_id)
        return True

    def get_model_info(self, model_id: str) -> ModelInfo | None:
        return SUPPORTED_MODELS.get(model_id)

    def get_download_progress(self, model_id: str) -> DownloadProgress | None:
        with self._lock:
            progress = self._downloads.get(model_id)
        return progress.snapshot() if progress else None

    def get_all_downloads(self) -> dict[str, DownloadProgress]:
        with self._lock:
            return {
                model_id: progress.snapshot()
                for model_id, progress in self._downloads.items()
            }

    def add_callback(self, callback: DownloadCallback) -> None:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_callback(self, callback: DownloadCallback) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _notify_callbacks(self, model_id: str, progress: DownloadProgress) -> None:
        with self._lock:
            callbacks = [
                *self._callbacks,
                *self._download_callbacks.get(model_id, []),
            ]
        snapshot = progress.snapshot()
        for callback in callbacks:
            try:
                callback(model_id, snapshot)
            except Exception:
                logger.exception("模型下载回调执行失败: %s", model_id)


_downloader: ModelDownloader | None = None


def get_model_downloader(models_dir: str | None = None) -> ModelDownloader:
    """Return the process-wide downloader instance."""
    global _downloader
    if _downloader is None:
        _downloader = ModelDownloader(models_dir)
    return _downloader
