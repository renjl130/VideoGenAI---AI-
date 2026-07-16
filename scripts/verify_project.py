"""VideoGenAI code and runtime-host readiness verification."""

import argparse
import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

Check = tuple[str, Callable[[], bool]]


def check_python_version() -> bool:
    from utils.runtime_environment import is_supported_python

    version = sys.version_info
    supported = is_supported_python()
    status = "OK" if supported else "FAIL"
    print(f"  {status}: Python {version.major}.{version.minor}.{version.micro}")
    return supported


def check_dependencies() -> bool:
    required = {
        "PySide6": "PySide6",
        "torch": "torch",
        "diffusers": "diffusers",
        "transformers": "transformers",
        "PIL": "Pillow",
        "numpy": "numpy",
        "peft": "peft",
        "safetensors": "safetensors",
    }
    missing = [
        package for module, package in required.items() if importlib.util.find_spec(module) is None
    ]
    if missing:
        print(f"  FAIL: Missing packages: {', '.join(missing)}")
        return False
    print("  OK: Required runtime packages are installed")
    return True


def check_directory_structure() -> bool:
    required = [
        "main.py",
        "launcher.py",
        "requirements.txt",
        "scripts/setup_environment.py",
        "utils/runtime_environment.py",
        "requirements-torch-cpu.txt",
        "requirements-torch-cu128.txt",
        "configs/default_config.json",
        "ui/main_window.py",
        "backend/engine_manager.py",
        "engines/base_engine.py",
        "engines/wan_engine.py",
        "utils/config_manager.py",
        "utils/paths.py",
        "utils/model_downloader.py",
        "utils/task_queue.py",
        "plugins/plugin_manifest.py",
        "plugins/example.plugin.json",
    ]
    missing = [item for item in required if not (PROJECT_ROOT / item).exists()]
    if missing:
        print(f"  FAIL: Missing project paths: {', '.join(missing)}")
        return False
    print("  OK: Required project paths exist")
    return True


def check_imports() -> bool:
    modules = [
        "utils.config_manager",
        "utils.logger",
        "utils.task_queue",
        "utils.lora_manager",
        "utils.history_manager",
        "utils.runtime_environment",
        "engines.base_engine",
        "plugins.base_plugin",
        "plugins.plugin_manifest",
        "plugins.plugin_manager",
    ]
    failures = []
    for module in modules:
        try:
            __import__(module)
        except Exception as error:
            failures.append(f"{module}: {error}")
    if failures:
        print("  FAIL: " + "; ".join(failures))
        return False
    print("  OK: Core modules import successfully")
    return True


def check_config() -> bool:
    try:
        from utils.config_manager import get_config

        config = get_config()
        if config.app.name != "VideoGenAI":
            print(f"  FAIL: Unexpected app name: {config.app.name}")
            return False
        config.resolve_path("models.models_dir", "./models")
    except Exception as error:
        print(f"  FAIL: Configuration error: {error}")
        return False
    print("  OK: Configuration is valid")
    return True


def check_cuda_runtime() -> bool:
    from utils.runtime_environment import inspect_runtime_environment

    environment = inspect_runtime_environment()
    print(f"  Python: {environment.python_version}")
    print(f"  PyTorch: {environment.torch_version or 'not installed'}")
    print(f"  PyTorch CUDA: {environment.torch_cuda_version or 'none'}")
    if environment.nvidia_gpu_names:
        print(f"  NVIDIA GPU: {', '.join(environment.nvidia_gpu_names)}")
    if not environment.cuda_available:
        for issue in environment.issues:
            print(f"  FAIL: {issue}")
        print("        Repair command:")
        print("        python scripts/setup_environment.py --backend cuda --force-torch")
        return False

    import torch

    for device_id in range(environment.cuda_device_count):
        properties = torch.cuda.get_device_properties(device_id)
        memory_gib = properties.total_memory / 1024**3
        print(
            f"  OK: CUDA device {device_id}: "
            f"{torch.cuda.get_device_name(device_id)} ({memory_gib:.1f} GiB)"
        )
    return True


def check_default_model() -> bool:
    try:
        from utils.config_manager import get_config
        from utils.model_downloader import get_model_downloader

        config = get_config()
        models_dir = config.resolve_path("models.models_dir", "./models")
        downloader = get_model_downloader(str(models_dir))
        downloader.refresh()
        model_id = config.models.default_model
        status = downloader.get_model_status(model_id)
    except Exception as error:
        print(f"  FAIL: Model validation error: {error}")
        return False

    if not downloader.is_model_downloaded(model_id):
        print(f"  FAIL: Default model {model_id} is {status.value}")
        print("        Complete or restart the model download before generation.")
        return False
    print(f"  OK: Default model {model_id} is complete")
    return True


def run_checks(checks: list[Check]) -> bool:
    results = []
    for index, (label, check) in enumerate(checks, start=1):
        print()
        print(f"[{index}/{len(checks)}] {label}")
        try:
            passed = bool(check())
        except Exception as error:
            print(f"  FAIL: Unexpected verifier error: {error}")
            passed = False
        results.append((label, passed))

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    for label, passed in results:
        print(f"  {label}: {'PASS' if passed else 'FAIL'}")
    print()
    print(f"  Total: {sum(passed for _, passed in results)}/{len(results)} passed")
    return all(passed for _, passed in results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("code", "environment", "runtime"),
        default="runtime",
        help=(
            "code checks source prerequisites; environment also requires CUDA; "
            "runtime additionally requires a complete model"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks: list[Check] = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Directory structure", check_directory_structure),
        ("Core imports", check_imports),
        ("Configuration", check_config),
    ]
    if args.mode in {"environment", "runtime"}:
        checks.append(("CUDA runtime", check_cuda_runtime))
    if args.mode == "runtime":
        checks.append(("Default model", check_default_model))

    print("=" * 60)
    print(f"VideoGenAI verification mode: {args.mode}")
    print("=" * 60)
    passed = run_checks(checks)
    print()
    if passed:
        print("Verification passed.")
        return 0
    print("Verification failed. Resolve the failures above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
