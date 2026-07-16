"""Runtime environment diagnostics and reproducible PyTorch installation plans."""

from __future__ import annotations

import importlib.metadata
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from utils.paths import PROJECT_ROOT

MIN_PYTHON = (3, 10)
MAX_PYTHON = (3, 14)
PYTORCH_VERSION = "2.11.0"
TORCHVISION_VERSION = "0.26.0"
TORCHAUDIO_VERSION = "2.11.0"
CUDA_WHEEL_CHANNEL = "cu128"
PYTORCH_INDEX_URL = f"https://download.pytorch.org/whl/{CUDA_WHEEL_CHANNEL}"


@dataclass(frozen=True)
class RuntimeEnvironment:
    """Facts required to decide whether local CUDA inference can run."""

    python_version: str
    python_supported: bool
    executable: str
    torch_installed: bool
    torch_version: str | None
    torch_cuda_version: str | None
    cuda_available: bool
    cuda_device_count: int
    nvidia_driver_available: bool
    nvidia_gpu_names: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def inference_ready(self) -> bool:
        return self.python_supported and self.cuda_available and not self.issues

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_supported_python(version_info: tuple[int, ...] | None = None) -> bool:
    """Return whether Python is within the project's tested release range."""
    version = version_info or tuple(sys.version_info[:3])
    major_minor = tuple(version[:2])
    return MIN_PYTHON <= major_minor <= MAX_PYTHON


def _nvidia_gpu_names() -> tuple[bool, tuple[str, ...]]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return False, ()
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False, ()
    names = tuple(line.strip() for line in result.stdout.splitlines() if line.strip())
    return result.returncode == 0 and bool(names), names


def inspect_runtime_environment() -> RuntimeEnvironment:
    """Inspect Python, the installed PyTorch build, and NVIDIA driver visibility."""
    python_supported = is_supported_python()
    driver_available, gpu_names = _nvidia_gpu_names()
    torch_installed = False
    torch_version: str | None = None
    torch_cuda_version: str | None = None
    cuda_available = False
    cuda_device_count = 0
    issues: list[str] = []

    try:
        import torch
    except ImportError:
        issues.append("PyTorch is not installed")
    else:
        torch_installed = True
        torch_version = str(torch.__version__)
        torch_cuda_version = torch.version.cuda
        cuda_available = bool(torch.cuda.is_available())
        cuda_device_count = int(torch.cuda.device_count()) if cuda_available else 0
        if driver_available and not cuda_available:
            if torch_cuda_version is None or "+cpu" in torch_version:
                issues.append("CPU-only PyTorch is installed while an NVIDIA GPU is available")
            else:
                issues.append("PyTorch includes CUDA but cannot initialize the NVIDIA runtime")
        elif not driver_available:
            issues.append("NVIDIA GPU/driver was not detected")

    if not python_supported:
        issues.append(
            f"Python {sys.version_info.major}.{sys.version_info.minor} is unsupported; "
            f"use Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} through "
            f"{MAX_PYTHON[0]}.{MAX_PYTHON[1]}"
        )

    return RuntimeEnvironment(
        python_version=sys.version.split()[0],
        python_supported=python_supported,
        executable=sys.executable,
        torch_installed=torch_installed,
        torch_version=torch_version,
        torch_cuda_version=torch_cuda_version,
        cuda_available=cuda_available,
        cuda_device_count=cuda_device_count,
        nvidia_driver_available=driver_available,
        nvidia_gpu_names=gpu_names,
        issues=tuple(issues),
    )


def torch_requirements_path(*, cuda: bool = True) -> Path:
    filename = "requirements-torch-cu128.txt" if cuda else "requirements-torch-cpu.txt"
    return PROJECT_ROOT / filename


def build_pip_install_command(
    requirements_path: Path,
    *,
    python_executable: str | None = None,
    upgrade: bool = True,
    force_reinstall: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """Build a shell-safe pip command as an argv list."""
    command = [python_executable or sys.executable, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    if force_reinstall:
        command.append("--force-reinstall")
    if dry_run:
        command.append("--dry-run")
    command.extend(["-r", str(requirements_path.resolve())])
    return command


def installed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None
