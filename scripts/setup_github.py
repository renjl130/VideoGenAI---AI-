"""
GitHub仓库设置脚本
"""

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent


def run_cmd(cmd, cwd=None):
    """运行命令"""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or project_root, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True


def check_git():
    """检查Git"""
    result = subprocess.run("git --version", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("Git not found. Please install Git first.")
        print("Download: https://git-scm.com/downloads")
        return False
    print(f"Git found: {result.stdout.strip()}")
    return True


def init_repo():
    """初始化Git仓库"""
    print("\nInitializing Git repository...")

    if (project_root / ".git").exists():
        print("Git repository already exists")
        return True

    if not run_cmd("git init"):
        return False

    print("Git repository initialized")
    return True


def create_initial_commit():
    """创建初始提交"""
    print("\nCreating initial commit...")

    if not run_cmd("git add ."):
        return False

    if not run_cmd('git commit -m "Initial commit: VideoGenAI v1.0.0"'):
        return False

    print("Initial commit created")
    return True


def add_remote(repo_url):
    """添加远程仓库"""
    print(f"\nAdding remote: {repo_url}")

    # 检查是否已有远程仓库
    result = subprocess.run(
        "git remote -v", shell=True, cwd=project_root, capture_output=True, text=True
    )

    if "origin" in result.stdout:
        print("Remote 'origin' already exists, updating...")
        if not run_cmd(f"git remote set-url origin {repo_url}"):
            return False
    else:
        if not run_cmd(f"git remote add origin {repo_url}"):
            return False

    print("Remote added successfully")
    return True


def push_to_github():
    """推送到GitHub"""
    print("\nPushing to GitHub...")

    if not run_cmd("git branch -M main"):
        return False

    if not run_cmd("git push -u origin main"):
        print("\nPush failed. You may need to:")
        print("1. Create the repository on GitHub first")
        print("2. Configure your Git credentials")
        print("3. Run: git push -u origin main")
        return False

    print("Pushed to GitHub successfully!")
    return True


def main():
    print("=" * 60)
    print("  VideoGenAI GitHub Setup")
    print("=" * 60)

    if not check_git():
        return 1

    if not init_repo():
        return 1

    # 获取仓库URL
    print("\n" + "-" * 60)
    print("Please create a new repository on GitHub first:")
    print("  1. Go to https://github.com/new")
    print("  2. Name: VideoGenAI")
    print("  3. Description: Local AI Video Generation Software")
    print("  4. Public or Private")
    print("  5. Do NOT initialize with README")
    print("-" * 60)

    repo_url = input("\nEnter your GitHub repository URL: ").strip()

    if not repo_url:
        print("No URL provided. Exiting.")
        return 1

    if not add_remote(repo_url):
        return 1

    if not create_initial_commit():
        return 1

    if not push_to_github():
        return 1

    print("\n" + "=" * 60)
    print("  Setup Complete!")
    print("=" * 60)
    print(f"\nYour repository: {repo_url}")
    print("\nNext steps:")
    print("  1. Add a description on GitHub")
    print("  2. Add topics: video-generation, ai, wan21, diffusion")
    print("  3. Create a release for v1.0.0")

    return 0


if __name__ == "__main__":
    sys.exit(main())
