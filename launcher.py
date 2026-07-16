"""
VideoGenAI 启动器
双击即可启动应用程序
"""
import sys
import os
import subprocess
from pathlib import Path


def get_python_exe():
    """获取Python可执行文件路径"""
    # 优先使用虚拟环境
    venv_path = Path(__file__).parent / ".venv"
    if venv_path.exists():
        if sys.platform == "win32":
            return str(venv_path / "Scripts" / "python.exe")
        else:
            return str(venv_path / "bin" / "python")
    
    # 使用系统Python
    return sys.executable


def check_venv():
    """检查虚拟环境"""
    venv_path = Path(__file__).parent / ".venv"
    return venv_path.exists()


def create_venv():
    """创建虚拟环境"""
    print("正在创建虚拟环境...")
    subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    print("虚拟环境创建完成")


def install_dependencies():
    """安装依赖"""
    python_exe = get_python_exe()
    requirements = Path(__file__).parent / "requirements.txt"
    
    if requirements.exists():
        print("正在安装依赖...")
        subprocess.run([
            python_exe, "-m", "pip", "install", "-r", str(requirements)
        ], check=True)
        print("依赖安装完成")
    else:
        print("警告: requirements.txt 不存在")


def check_torch_cuda():
    """检查PyTorch CUDA支持"""
    python_exe = get_python_exe()
    
    try:
        result = subprocess.run([
            python_exe, "-c", 
            "import torch; print('CUDA:', torch.cuda.is_available()); "
            "print('Version:', torch.__version__)"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            return "True" in result.stdout
    except Exception:
        pass
    
    return False


def install_torch_cuda():
    """安装CUDA版本的PyTorch"""
    python_exe = get_python_exe()
    
    print("正在安装 CUDA 版本的 PyTorch...")
    subprocess.run([
        python_exe, "-m", "pip", "install", 
        "torch", "torchvision", "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu121"
    ], check=True)
    print("PyTorch CUDA 安装完成")


def main():
    """主函数"""
    print("=" * 50)
    print("VideoGenAI 启动器")
    print("=" * 50)
    print()
    
    # 切换到项目目录
    os.chdir(Path(__file__).parent)
    
    # 检查虚拟环境
    if not check_venv():
        print("首次运行，正在初始化...")
        create_venv()
        install_dependencies()
        
        # 检查并安装CUDA PyTorch
        if not check_torch_cuda():
            install_torch_cuda()
        
        print()
        print("初始化完成！")
        print()
    
    # 启动主程序
    print("正在启动 VideoGenAI...")
    python_exe = get_python_exe()
    
    try:
        subprocess.run([python_exe, "main.py"], check=True)
    except KeyboardInterrupt:
        print("\n程序已退出")
    except Exception as e:
        print(f"\n启动失败: {e}")
        print("请尝试手动运行: python main.py")
        input("按 Enter 键退出...")


if __name__ == "__main__":
    main()
