"""
VideoGenAI - 本地AI视频生成软件
主程序入口
"""
import sys
import os
from pathlib import Path

# 抑制pynvml弃用警告
os.environ["PYNVML_SUPPRESS_WARNINGS"] = "1"

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


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
        print("缺少以下依赖:")
        for dep in missing:
            print(f"  - {dep}")
        print()
        print("请运行以下命令安装:")
        print("  pip install -r requirements.txt")
        print("=" * 50)
        return False
    
    return True


def check_gpu():
    """检查GPU"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"检测到GPU: {gpu_name}")
            print(f"显存: {gpu_memory:.1f} GB")
            return True
        else:
            print("警告: 未检测到CUDA GPU，将使用CPU（速度会很慢）")
            return True
    except Exception as e:
        print(f"检查GPU失败: {e}")
        return True


def setup_environment():
    """设置环境"""
    # 创建必要的目录
    dirs = ["models", "loras", "outputs", "configs", "cache", "logs"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    # 设置环境变量
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def main():
    """主函数"""
    print("=" * 50)
    print("VideoGenAI - 本地AI视频生成软件")
    print("版本: 1.0.0")
    print("=" * 50)
    print()
    
    # 检查依赖
    print("检查依赖...")
    if not check_dependencies():
        sys.exit(1)
    print("依赖检查通过")
    print()
    
    # 检查GPU
    print("检查GPU...")
    check_gpu()
    print()
    
    # 设置环境
    print("设置环境...")
    setup_environment()
    print("环境设置完成")
    print()
    
    # 启动GUI
    print("启动图形界面...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        
        from ui.main_window import MainWindow, MODERN_DARK_THEME
        
        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName("VideoGenAI")
        app.setApplicationVersion("1.0.0")
        
        # 设置字体
        font = QFont("Microsoft YaHei", 10)
        app.setFont(font)
        
        # 应用深色主题
        app.setStyleSheet(MODERN_DARK_THEME)
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        print("图形界面已启动")
        print()
        
        # 运行应用
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
