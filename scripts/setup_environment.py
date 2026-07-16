"""Create or repair a reproducible VideoGenAI Python environment."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.runtime_environment import (  # noqa: E402
    build_pip_install_command,
    is_supported_python,
    torch_requirements_path,
)


def venv_python(venv_path: Path) -> Path:
    """Return the platform-specific interpreter inside a virtual environment."""
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def run_command(command: list[str], *, dry_run: bool) -> None:
    """Print every command and execute it without invoking a shell."""
    print("+", subprocess.list2cmdline(command))
    if not dry_run:
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def build_setup_commands(
    *,
    host_python: str,
    target_venv: Path,
    backend: str,
    force_torch: bool,
    dry_run: bool,
) -> list[list[str]]:
    """Build deterministic setup commands for tests and CLI execution."""
    target_python = venv_python(target_venv)
    commands: list[list[str]] = []
    target_exists = target_python.exists()
    if not target_exists:
        commands.append([host_python, "-m", "venv", str(target_venv)])
    command_python = str(target_python if target_exists or not dry_run else Path(host_python))

    bootstrap_command = [
        command_python,
        "-m",
        "pip",
        "install",
        "--upgrade",
    ]
    if dry_run:
        bootstrap_command.append("--dry-run")
    bootstrap_command.extend(["pip", "setuptools", "wheel"])
    commands.append(bootstrap_command)
    commands.append(
        build_pip_install_command(
            torch_requirements_path(cuda=backend == "cuda"),
            python_executable=command_python,
            force_reinstall=force_torch,
            dry_run=dry_run,
        )
    )
    commands.append(
        build_pip_install_command(
            PROJECT_ROOT / "requirements.txt",
            python_executable=command_python,
            dry_run=dry_run,
        )
    )
    verification_mode = "environment" if backend == "cuda" else "code"
    commands.append(
        [
            command_python,
            str(PROJECT_ROOT / "scripts" / "verify_project.py"),
            "--mode",
            verification_mode,
        ]
    )
    return commands


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=("cuda", "cpu"),
        default="cuda",
        help="Install the official CUDA 12.8 or CPU-only PyTorch wheel set.",
    )
    parser.add_argument(
        "--venv",
        default=".venv",
        help="Virtual-environment path, relative to the project root by default.",
    )
    parser.add_argument(
        "--force-torch",
        action="store_true",
        help="Force reinstall the pinned PyTorch stack (useful when replacing a CPU build).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands and ask pip to resolve packages without installing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not is_supported_python():
        print(
            "Unsupported host Python. VideoGenAI requires Python 3.10 through 3.14; "
            f"detected {sys.version.split()[0]}."
        )
        return 2

    target_venv = Path(args.venv).expanduser()
    if not target_venv.is_absolute():
        target_venv = PROJECT_ROOT / target_venv
    target_venv = target_venv.resolve()

    commands = build_setup_commands(
        host_python=sys.executable,
        target_venv=target_venv,
        backend=args.backend,
        force_torch=args.force_torch,
        dry_run=args.dry_run,
    )
    try:
        for command in commands:
            is_pip_install = command[1:4] == ["-m", "pip", "install"]
            run_command(command, dry_run=args.dry_run and not is_pip_install)
    except subprocess.CalledProcessError as error:
        print(f"Environment setup failed with exit code {error.returncode}.")
        return error.returncode or 1

    print("Environment setup completed." if not args.dry_run else "Dry run completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
