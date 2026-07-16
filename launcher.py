"""VideoGenAI launcher with explicit environment readiness checks."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PATH = PROJECT_ROOT / ".venv"


def venv_python_path() -> Path:
    relative = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    return VENV_PATH / relative


def get_python_exe() -> str:
    candidate = venv_python_path()
    return str(candidate if candidate.is_file() else Path(sys.executable))


def check_venv() -> bool:
    return venv_python_path().is_file()


def create_environment() -> None:
    """Create the pinned CUDA environment through the maintained setup workflow."""
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "setup_environment.py"),
        "--backend",
        "cuda",
        "--venv",
        str(VENV_PATH),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def verify_environment() -> bool:
    result = subprocess.run(
        [
            get_python_exe(),
            str(PROJECT_ROOT / "scripts" / "verify_project.py"),
            "--mode",
            "environment",
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode == 0


def print_repair_command() -> None:
    print()
    print("VideoGenAI cannot start GPU inference with the current environment.")
    print("Run this repair command from the project directory:")
    print(
        subprocess.list2cmdline(
            [
                get_python_exe(),
                "scripts/setup_environment.py",
                "--backend",
                "cuda",
                "--force-torch",
            ]
        )
    )


def main() -> int:
    os.chdir(PROJECT_ROOT)
    print("=" * 50)
    print("VideoGenAI Launcher")
    print("=" * 50)

    try:
        if not check_venv():
            print("No project virtual environment found; creating the pinned CUDA environment.")
            create_environment()
        if not verify_environment():
            print_repair_command()
            return 2
        subprocess.run([get_python_exe(), str(PROJECT_ROOT / "main.py")], check=True)
        return 0
    except KeyboardInterrupt:
        print()
        print("VideoGenAI exited.")
        return 130
    except subprocess.CalledProcessError as error:
        print()
        print(f"Launcher command failed with exit code {error.returncode}.")
        return error.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
