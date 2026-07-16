"""
打包脚本 - 使用PyInstaller创建可执行文件
"""
import subprocess
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent


def install_pyinstaller():
    """安装PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "pyinstaller"
    ], check=True)
    print("PyInstaller installed")


def build_exe():
    """构建可执行文件"""
    print("\nBuilding executable...")
    
    # PyInstaller参数
    args = [
        sys.executable, "-m", "PyInstaller",
        "--name=VideoGenAI",
        "--windowed",  # 无控制台窗口
        "--onedir",    # 单目录打包
        "--icon=NONE",  # 可以添加图标
        "--add-data=configs;configs",
        "--add-data=plugins;plugins",
        "--hidden-import=PySide6",
        "--hidden-import=torch",
        "--hidden-import=diffusers",
        "--hidden-import=transformers",
        "--collect-all=diffusers",
        "--collect-all=transformers",
        "main.py"
    ]
    
    # Windows特定参数
    if sys.platform == "win32":
        args.append("--noconsole")
    
    result = subprocess.run(args, cwd=project_root)
    
    if result.returncode != 0:
        print("Build failed!")
        return False
    
    print("\nBuild successful!")
    print(f"Output: {project_root / 'dist' / 'VideoGenAI'}")
    return True


def create_portable_package():
    """创建便携版包"""
    print("\nCreating portable package...")
    
    dist_dir = project_root / "dist" / "VideoGenAI"
    
    # 复制必要的目录
    import shutil
    
    for d in ["models", "loras", "outputs", "configs", "cache", "logs"]:
        src = project_root / d
        dst = dist_dir / d
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.mkdir(exist_ok=True)
    
    # 创建启动脚本
    launcher = dist_dir / "run.bat"
    launcher.write_text("""@echo off
cd /d "%~dp0"
start VideoGenAI.exe
""", encoding='utf-8')
    
    print(f"Portable package created at: {dist_dir}")
    return True


def main():
    print("=" * 60)
    print("  VideoGenAI Build Script")
    print("=" * 60)
    
    try:
        install_pyinstaller()
        
        if not build_exe():
            return 1
        
        if not create_portable_package():
            return 1
        
        print("\n" + "=" * 60)
        print("  Build Complete!")
        print("=" * 60)
        print(f"\nExecutable: {project_root / 'dist' / 'VideoGenAI' / 'VideoGenAI.exe'}")
        print("\nTo distribute:")
        print("  1. Zip the 'dist/VideoGenAI' folder")
        print("  2. Users extract and run 'VideoGenAI.exe'")
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
