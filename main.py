"""
VideoGenAI - 本地AI视频生成软件
主程序入口
"""
import sys
import os
import warnings
from pathlib import Path

# 抑制警告
warnings.filterwarnings("ignore", message=".*pynvml.*")
os.environ["PYNVML_SUPPRESS_WARNINGS"] = "1"

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.i18n import I18n, t


def check_dependencies():
    """检查依赖"""
    missing = []
    
    try:
        import PySide6
    except ImportError:
        missing.append("PySide6")
    
    try:
        import torch
    except ImportError:
        missing.append("torch")
    
    try:
        import diffusers
    except ImportError:
        missing.append("diffusers")
    
    try:
        import transformers
    except ImportError:
        missing.append("transformers")
    
    if missing:
        print("=" * 50)
        print("缺少以下依赖 / Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print()
        print("请运行以下命令安装 / Please install:")
        print("  pip install -r requirements.txt")
        print("=" * 50)
        return False
    
    return True


def check_gpu():
    """检查GPU"""
    from utils.gpu_monitor import get_gpu_monitor, format_memory
    
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
        print(f"  检测方法: {detection_info['method']}")
        print("  请确保已安装NVIDIA驱动和CUDA")
        print("  Please ensure NVIDIA drivers and CUDA are installed")
        return False


def setup_environment():
    """设置环境"""
    # 创建必要的目录
    dirs = ["models", "loras", "outputs", "configs", "cache", "logs"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    # 设置环境变量
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def load_language_setting():
    """加载语言设置"""
    try:
        import json
        config_path = project_root / "configs" / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                lang = config.get("app", {}).get("language", "zh_CN")
                I18n.set_language(lang)
    except:
        pass


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
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        from ui.main_window import MainWindow, ELEGANT_THEME
        
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
