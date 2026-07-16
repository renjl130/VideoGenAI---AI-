import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.setup_environment import build_setup_commands, venv_python
from utils.runtime_environment import (
    CUDA_WHEEL_CHANNEL,
    PYTORCH_INDEX_URL,
    RuntimeEnvironment,
    build_pip_install_command,
    inspect_runtime_environment,
    is_supported_python,
    torch_requirements_path,
)


def test_supported_python_range_is_explicit():
    assert is_supported_python((3, 10, 0))
    assert is_supported_python((3, 14, 99))
    assert not is_supported_python((3, 9, 20))
    assert not is_supported_python((3, 15, 0))


def test_cuda_requirement_and_pip_command_are_pinned_and_shell_safe():
    path = torch_requirements_path(cuda=True)
    text = path.read_text(encoding="utf-8")

    assert CUDA_WHEEL_CHANNEL == "cu128"
    assert PYTORCH_INDEX_URL in text
    assert "torch==2.11.0" in text
    assert "torchvision==0.26.0" in text
    assert "torchaudio==2.11.0" in text
    command = build_pip_install_command(
        path,
        python_executable="python.exe",
        force_reinstall=True,
        dry_run=True,
    )
    assert command == [
        "python.exe",
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--force-reinstall",
        "--dry-run",
        "-r",
        str(path.resolve()),
    ]


def test_setup_commands_install_torch_before_application_dependencies(tmp_path: Path):
    target_venv = tmp_path / ".venv"
    commands = build_setup_commands(
        host_python="host-python.exe",
        target_venv=target_venv,
        backend="cuda",
        force_torch=True,
        dry_run=True,
    )

    assert commands[0] == ["host-python.exe", "-m", "venv", str(target_venv)]
    assert commands[1][0] == "host-python.exe"
    assert str(torch_requirements_path(cuda=True)) in commands[2]
    assert (
        str((Path(__file__).resolve().parent.parent / "requirements.txt").resolve()) in commands[3]
    )
    assert commands[4][-2:] == ["--mode", "environment"]


def test_existing_venv_uses_its_interpreter_for_setup(tmp_path: Path):
    target_venv = tmp_path / ".venv"
    target_python = venv_python(target_venv)
    target_python.parent.mkdir(parents=True)
    target_python.touch()

    commands = build_setup_commands(
        host_python="host-python.exe",
        target_venv=target_venv,
        backend="cpu",
        force_torch=False,
        dry_run=False,
    )

    assert all(command[0] == str(target_python) for command in commands)
    assert commands[-1][-1] == "code"


def test_runtime_environment_identifies_cpu_torch_with_visible_nvidia_gpu():
    fake_torch = SimpleNamespace(
        __version__="2.11.0+cpu",
        version=SimpleNamespace(cuda=None),
        cuda=SimpleNamespace(is_available=lambda: False, device_count=lambda: 0),
    )
    with (
        patch.dict(sys.modules, {"torch": fake_torch}),
        patch(
            "utils.runtime_environment._nvidia_gpu_names",
            return_value=(True, ("Test GPU",)),
        ),
    ):
        environment = inspect_runtime_environment()

    assert environment.nvidia_driver_available
    assert environment.nvidia_gpu_names == ("Test GPU",)
    assert not environment.cuda_available
    assert "CPU-only PyTorch" in environment.issues[0]
    assert not environment.inference_ready


def test_runtime_environment_ready_property():
    environment = RuntimeEnvironment(
        python_version="3.14.3",
        python_supported=True,
        executable="python.exe",
        torch_installed=True,
        torch_version="2.11.0+cu128",
        torch_cuda_version="12.8",
        cuda_available=True,
        cuda_device_count=1,
        nvidia_driver_available=True,
        nvidia_gpu_names=("Test GPU",),
        issues=(),
    )

    assert environment.inference_ready
    assert environment.to_dict()["cuda_device_count"] == 1
