"""
VideoGenAI - 本地AI视频生成软件
主程序入口
"""

import importlib.util
import os
import sys
import warnings

from utils.config_manager import get_config
from utils.i18n import I18n, t
from utils.paths import APP_PATHS

# 抑制警告
warnings.filterwarnings("ignore", message=".*pynvml.*")
os.environ["PYNVML_SUPPRESS_WARNINGS"] = "1"

project_root = APP_PATHS.root


def check_dependencies():
    """检查运行时依赖是否可发现。"""
    dependencies = ("PySide6", "torch", "diffusers", "transformers")
    missing = [
        dependency for dependency in dependencies if importlib.util.find_spec(dependency) is None
    ]

    if missing:
        print("=" * 50)
        print("缺少以下依赖 / Missing dependencies:")
        for dependency in missing:
            print(f"  - {dependency}")
        print()
        print("请运行以下命令安装 / Please install:")
        print("  pip install -r requirements.txt")
        print("=" * 50)
        return False

    return True


def check_gpu():
    """检查GPU"""
    from utils.gpu_monitor import get_gpu_monitor

    monitor = get_gpu_monitor()
    detection_info = monitor.get_detection_info()

    if detection_info["gpu_count"] > 0:
        for i, name in enumerate(detection_info["gpu_names"]):
            info = monitor.get_gpu_info(i)
            if info:
                print(t("gpu_detected", name=name))
                print(t("gpu_vram", size=info.total_memory / 1024))
            else:
                print(f"GPU {i}: {name}")
        return True
    else:
        print(t("gpu_not_found"))
        print(f"  检测方法: {detection_info.get('method', 'nvidia-smi/PyTorch')}")
        print("  请确保已安装NVIDIA驱动和CUDA")
        print("  Please ensure NVIDIA drivers and CUDA are installed")
        return False


def setup_environment():
    """设置环境"""
    # 创建必要的目录
    directories = (
        APP_PATHS.models,
        APP_PATHS.loras,
        APP_PATHS.outputs,
        APP_PATHS.configs,
        APP_PATHS.cache,
        APP_PATHS.logs,
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    # 设置环境变量
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def load_language_setting():
    """从统一配置管理器加载语言。"""
    try:
        I18n.set_language(get_config().app.language)
    except Exception as error:
        warnings.warn(f"加载语言配置失败: {error}", RuntimeWarning, stacklevel=2)


def main():
    """主函数"""
    # 加载语言设置
    load_language_setting()

    print("=" * 50)
    print(t("app_title"))
    print(t("app_version"))
    print("=" * 50)
    print()

    # 检查依赖
    print(t("check_deps"))
    if not check_dependencies():
        sys.exit(1)
    print(t("deps_ok"))
    print()

    # 检查GPU
    print(t("check_gpu"))
    check_gpu()
    print()

    # 设置环境
    print(t("setup_env"))
    setup_environment()
    print(t("env_ok"))
    print()

    # 启动GUI
    print(t("start_gui"))

    try:
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QApplication

        from ui.main_window import ELEGANT_THEME, MainWindow

        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName("VideoGenAI")
        app.setApplicationVersion("1.0.0")

        # 设置字体
        font = QFont("Microsoft YaHei", 10)
        app.setFont(font)

        # 应用深色主题
        app.setStyleSheet(ELEGANT_THEME)

        # 创建主窗口
        window = MainWindow()
        window.show()

        print(t("gui_ok"))
        print()

        # 运行应用
        sys.exit(app.exec())

    except Exception as e:
        print(t("start_failed", error=e))
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
