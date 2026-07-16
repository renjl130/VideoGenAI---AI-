"""Safe local LoRA discovery and validation for Wan pipelines."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from safetensors import safe_open

from utils.logger import get_logger
from utils.paths import APP_PATHS, resolve_project_path

logger = get_logger("lora")
_SUPPORTED_SUFFIXES = frozenset({".safetensors"})


@dataclass(frozen=True)
class LoraInfo:
    """Validated local LoRA metadata exposed to backend and UI layers."""

    lora_id: str
    name: str
    path: Path
    size_bytes: int
    tensor_count: int
    adapter_name: str


class LoraValidationError(ValueError):
    """Raised when a local LoRA file is unsafe or structurally invalid."""


class LoraManager:
    """Thread-safe registry that accepts only validated safetensors files."""

    _instance: ClassVar[LoraManager | None] = None
    _initialized: bool

    def __new__(cls, loras_dir: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, loras_dir: str | None = None):
        if self._initialized:
            return
        self._initialized = True
        self._root = resolve_project_path(loras_dir) if loras_dir else APP_PATHS.loras
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._loras: dict[str, LoraInfo] = {}
        self._invalid: dict[str, str] = {}
        self.refresh()

    @staticmethod
    def _adapter_name(lora_id: str) -> str:
        digest = hashlib.sha256(lora_id.encode("utf-8")).hexdigest()[:12]
        return f"videogenai_{digest}"

    def _relative_id(self, path: Path) -> str:
        relative = path.relative_to(self._root).with_suffix("")
        return relative.as_posix()

    def validate_file(self, path: Path) -> LoraInfo:
        """Validate one file without deserializing executable pickle content."""
        resolved = path.resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError as error:
            raise LoraValidationError("LoRA path escapes the configured directory") from error
        if path.is_symlink():
            raise LoraValidationError("symbolic-link LoRA files are not allowed")
        if resolved.suffix.lower() not in _SUPPORTED_SUFFIXES:
            raise LoraValidationError("only .safetensors LoRA files are supported")
        if not resolved.is_file() or resolved.stat().st_size <= 0:
            raise LoraValidationError("LoRA file is missing or empty")

        try:
            with safe_open(resolved, framework="pt", device="cpu") as checkpoint:
                keys = list(checkpoint.keys())
        except Exception as error:
            raise LoraValidationError(f"invalid safetensors checkpoint: {error}") from error
        if not keys:
            raise LoraValidationError("LoRA checkpoint contains no tensors")
        if not any("lora" in key.lower() for key in keys):
            raise LoraValidationError("checkpoint does not contain LoRA tensors")

        lora_id = self._relative_id(resolved)
        return LoraInfo(
            lora_id=lora_id,
            name=resolved.stem,
            path=resolved,
            size_bytes=resolved.stat().st_size,
            tensor_count=len(keys),
            adapter_name=self._adapter_name(lora_id),
        )

    def refresh(self) -> dict[str, LoraInfo]:
        """Rescan the directory and atomically publish the valid registry."""
        valid: dict[str, LoraInfo] = {}
        invalid: dict[str, str] = {}
        for path in sorted(self._root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _SUPPORTED_SUFFIXES:
                continue
            try:
                info = self.validate_file(path)
            except LoraValidationError as error:
                invalid[str(path)] = str(error)
                logger.warning("Ignoring invalid LoRA %s: %s", path, error)
            else:
                valid[info.lora_id] = info

        with self._lock:
            self._loras = valid
            self._invalid = invalid
            return dict(self._loras)

    def get_available_loras(self) -> dict[str, LoraInfo]:
        with self._lock:
            return dict(self._loras)

    def get_invalid_loras(self) -> dict[str, str]:
        with self._lock:
            return dict(self._invalid)

    def resolve(self, lora_id: str) -> LoraInfo:
        """Resolve only an ID from the validated registry, never an arbitrary path."""
        with self._lock:
            info = self._loras.get(lora_id)
        if info is None:
            raise KeyError(f"Unknown or invalid LoRA: {lora_id}")
        return info


_lora_manager: LoraManager | None = None


def get_lora_manager(loras_dir: str | None = None) -> LoraManager:
    global _lora_manager
    if _lora_manager is None:
        _lora_manager = LoraManager(loras_dir)
    return _lora_manager
