"""Run the reproducible VideoGenAI code-quality gate."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(label: str, command: list[str], env: dict[str, str]) -> bool:
    print()
    print(f"{'=' * 20} {label} {'=' * 20}")
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
    )
    if completed.returncode:
        print(f"{label} failed with exit code {completed.returncode}")
        return False
    print(f"{label} passed")
    return True


def main() -> int:
    python = sys.executable
    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    checks = [
        ("Ruff", [python, "-m", "ruff", "check", "."]),
        ("Mypy", [python, "-m", "mypy"]),
        ("Pytest", [python, "-m", "pytest", "-q"]),
        (
            "Code verification",
            [python, "scripts/verify_project.py", "--mode", "code"],
        ),
    ]
    results = [run(label, command, env) for label, command in checks]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
