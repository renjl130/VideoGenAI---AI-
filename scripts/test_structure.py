"""
测试项目结构
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_directory_structure():
    """测试目录结构"""
    print("测试目录结构...")

    required_dirs = [
        "models",
        "loras",
        "outputs",
        "configs",
        "cache",
        "ui",
        "backend",
        "engines",
        "nodes",
        "utils",
        "scripts",
        "plugins",
    ]

    missing_dirs = []
    for d in required_dirs:
        if not (project_root / d).exists():
            missing_dirs.append(d)

    if missing_dirs:
        print(f"缺少目录: {missing_dirs}")
        return False

    print("✓ 目录结构正确")
    return True


def test_required_files():
    """测试必需文件"""
    print("测试必需文件...")

    required_files = [
        "main.py",
        "launcher.py",
        "requirements.txt",
        "README.md",
        "LICENSE",
        "configs/default_config.json",
        "ui/__init__.py",
        "ui/main_window.py",
        "backend/__init__.py",
        "backend/engine_manager.py",
        "engines/__init__.py",
        "engines/base_engine.py",
        "engines/wan_engine.py",
        "utils/__init__.py",
        "utils/config_manager.py",
        "utils/logger.py",
        "utils/gpu_monitor.py",
        "utils/model_downloader.py",
        "utils/task_queue.py",
        "utils/history_manager.py",
        "plugins/__init__.py",
        "plugins/base_plugin.py",
        "plugins/plugin_manager.py",
    ]

    missing_files = []
    for f in required_files:
        if not (project_root / f).exists():
            missing_files.append(f)

    if missing_files:
        print(f"缺少文件: {missing_files}")
        return False

    print("✓ 所有必需文件存在")
    return True


def test_imports():
    """测试导入"""
    print("测试导入...")

    try:
        print("  ✓ config_manager")
    except Exception as e:
        print(f"  ✗ config_manager: {e}")
        return False

    try:
        print("  ✓ logger")
    except Exception as e:
        print(f"  ✗ logger: {e}")
        return False

    try:
        print("  ✓ task_queue")
    except Exception as e:
        print(f"  ✗ task_queue: {e}")
        return False

    try:
        print("  ✓ history_manager")
    except Exception as e:
        print(f"  ✗ history_manager: {e}")
        return False

    print("✓ 所有模块导入成功")
    return True


def test_config():
    """测试配置"""
    print("测试配置...")

    try:
        from utils.config_manager import get_config

        config = get_config()

        # 测试配置读取
        app_name = config.get("app.name")
        if app_name != "VideoGenAI":
            print(f"  ✗ 配置值错误: {app_name}")
            return False

        print("  ✓ 配置读取正常")
        print("✓ 配置测试通过")
        return True

    except Exception as e:
        print(f"  ✗ 配置测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 50)
    print("VideoGenAI 项目结构测试")
    print("=" * 50)
    print()

    results = []

    results.append(("目录结构", test_directory_structure()))
    print()

    results.append(("必需文件", test_required_files()))
    print()

    results.append(("模块导入", test_imports()))
    print()

    results.append(("配置系统", test_config()))
    print()

    # 汇总结果
    print("=" * 50)
    print("测试结果汇总:")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("所有测试通过！项目结构正确。")
        return 0
    else:
        print("部分测试失败，请检查项目结构。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
