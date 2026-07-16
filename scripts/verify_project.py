"""
项目可行性验证脚本
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_python_version():
    """检查Python版本"""
    print("[1/6] Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"  FAIL: Python 3.10+ required, got {version.major}.{version.minor}")
        return False
    print(f"  OK: Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖"""
    print("\n[2/6] Checking dependencies...")
    
    required = [
        ("PySide6", "PySide6"),
        ("torch", "torch"),
        ("diffusers", "diffusers"),
        ("transformers", "transformers"),
        ("PIL", "Pillow"),
        ("numpy", "numpy"),
    ]
    
    missing = []
    for module, package in required:
        try:
            __import__(module)
            print(f"  OK: {package}")
        except ImportError:
            print(f"  MISSING: {package}")
            missing.append(package)
    
    if missing:
        print(f"\n  Install missing: pip install {' '.join(missing)}")
        return False
    return True

def check_gpu():
    """检查GPU"""
    print("\n[3/6] Checking GPU...")
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"  OK: {gpu_name}")
            print(f"  VRAM: {gpu_mem:.1f} GB")
            
            if gpu_mem < 6:
                print("  WARNING: Less than 6GB VRAM may cause issues")
            return True
        else:
            print("  WARNING: No CUDA GPU detected, will use CPU (very slow)")
            return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def check_directory_structure():
    """检查目录结构"""
    print("\n[4/6] Checking directory structure...")
    
    required_dirs = [
        "models", "loras", "outputs", "configs", "cache",
        "ui", "backend", "engines", "utils", "plugins", "scripts"
    ]
    
    required_files = [
        "main.py", "launcher.py", "requirements.txt", "README.md",
        "configs/default_config.json",
        "ui/__init__.py", "ui/main_window.py",
        "backend/__init__.py", "backend/engine_manager.py",
        "engines/__init__.py", "engines/base_engine.py", "engines/wan_engine.py",
        "utils/__init__.py", "utils/config_manager.py", "utils/logger.py",
        "utils/gpu_monitor.py", "utils/model_downloader.py",
        "utils/task_queue.py", "utils/history_manager.py",
        "plugins/__init__.py", "plugins/base_plugin.py", "plugins/plugin_manager.py"
    ]
    
    all_ok = True
    
    for d in required_dirs:
        if (project_root / d).is_dir():
            print(f"  OK: {d}/")
        else:
            print(f"  MISSING: {d}/")
            all_ok = False
    
    for f in required_files:
        if (project_root / f).is_file():
            print(f"  OK: {f}")
        else:
            print(f"  MISSING: {f}")
            all_ok = False
    
    return all_ok

def check_imports():
    """检查模块导入"""
    print("\n[5/6] Checking module imports...")
    
    modules = [
        "utils.config_manager",
        "utils.logger",
        "utils.task_queue",
        "utils.history_manager",
        "engines.base_engine",
        "plugins.base_plugin",
    ]
    
    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print(f"  OK: {module}")
        except Exception as e:
            print(f"  FAIL: {module} - {e}")
            all_ok = False
    
    return all_ok

def check_config():
    """检查配置"""
    print("\n[6/6] Checking configuration...")
    
    try:
        from utils.config_manager import get_config
        config = get_config()
        
        app_name = config.get("app.name")
        if app_name == "VideoGenAI":
            print("  OK: Config loaded correctly")
            return True
        else:
            print(f"  FAIL: Unexpected app name: {app_name}")
            return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def main():
    print("=" * 60)
    print("  VideoGenAI Project Verification")
    print("=" * 60)
    
    results = [
        check_python_version(),
        check_dependencies(),
        check_gpu(),
        check_directory_structure(),
        check_imports(),
        check_config()
    ]
    
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    labels = [
        "Python Version",
        "Dependencies",
        "GPU",
        "Directory Structure",
        "Module Imports",
        "Configuration"
    ]
    
    for label, result in zip(labels, results):
        status = "PASS" if result else "FAIL"
        print(f"  {label}: {status}")
    
    print(f"\n  Total: {passed}/{total} passed")
    
    if all(results):
        print("\n  All checks passed! Project is ready.")
        return 0
    else:
        print("\n  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
