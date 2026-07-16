"""
VideoGenAI 安装配置
"""

from pathlib import Path

from setuptools import find_packages, setup

# 读取README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# 读取requirements
requirements = []
req_file = this_directory / "requirements.txt"
if req_file.exists():
    with open(req_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # 处理带条件的依赖
                if ";" in line:
                    requirements.append(line)
                else:
                    requirements.append(line)

setup(
    name="videogenai",
    version="1.0.0",
    author="VideoGenAI Team",
    author_email="videogenai@example.com",
    description="本地AI视频生成软件",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/VideoGenAI",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "videogenai=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.md", "*.txt"],
    },
)
