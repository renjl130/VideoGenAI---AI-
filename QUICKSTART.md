# VideoGenAI 快速开始指南

## 开始前

- Windows 10/11，64 位；
- NVIDIA GPU。默认 Wan2.1-T2V-1.3B 建议至少 8 GiB 显存，并应使用低显存档位；
- Python 3.10–3.14，64 位；
- 默认模型完整下载约 **27 GiB**，请至少预留 60 GiB 可用磁盘空间。

> 仅在 `nvidia-smi` 中看到显卡并不表示 PyTorch 可以使用 CUDA。启动前应运行环境验证。

## 1. 安装或修复 CUDA 环境

在项目根目录执行：

```powershell
python scripts/setup_environment.py --backend cuda --venv .venv
```

如果已有虚拟环境安装了 CPU 版 PyTorch，请使用：

```powershell
.\.venv\Scripts\python.exe scripts/setup_environment.py --backend cuda --venv .venv --force-torch
```

也可以双击 `setup_cuda.bat`。安装完成后验证：

```powershell
.\.venv\Scripts\python.exe scripts/verify_project.py --mode environment
```

该命令必须显示 CUDA runtime 通过，才能进行视频推理。

## 2. 启动程序

- 双击 `start.bat`；或
- 在 PowerShell 运行：

```powershell
.\.venv\Scripts\python.exe launcher.py
```

`launcher.py` 会在启动前检查项目虚拟环境、CUDA PyTorch 和 NVIDIA 设备。不要用旧的通用 `pip install -r requirements.txt` 流程代替 CUDA 安装步骤，因为 `requirements.txt` 有意不包含 PyTorch。

## 3. 下载并加载模型

1. 在左侧模型区域选择 `wan2.1-t2v-1.3b`。
2. 点击“下载模型”。完整 Diffusers 包约 27 GiB；如果网络中断，保留的部分文件会在下次下载时续传。
3. 状态为“完整 / Ready”后，选择低显存性能档位并点击“加载模型”。
4. 输入 Prompt，建议先使用较低分辨率、17 或 21 帧及较少步数进行首个验证。

只有通过以下完整运行前检查后，才表示环境和默认模型均已准备好：

```powershell
.\.venv\Scripts\python.exe scripts/verify_project.py --mode runtime
```

## 常见问题

### CUDA runtime 校验失败

运行：

```powershell
.\.venv\Scripts\python.exe scripts/setup_environment.py --backend cuda --venv .venv --force-torch
```

然后重新执行 `scripts/verify_project.py --mode environment`。不要仅通过 UI 能启动就认定推理环境正确。

### 显存不足

1. 选择 `low_vram` 性能档位；
2. 使用 1.3B T2V 模型；
3. 降低分辨率、帧数和推理步数；
4. 确保没有其他程序占用显存；
5. 查看任务失败记录中的 OOM 诊断和建议。

### 模型下载失败或中断

再次点击“下载模型”即可续传。不要把未完成的模型目录手动标记为可用；应用会校验 Diffusers 配置、权重索引及分片完整性。

## 下一步

- 查看 `README.md` 了解完整配置和质量门禁；
- 在 `outputs/` 查看生成结果，在 `outputs/history/` 查看任务历史；
- 在调整模型、Scheduler、LoRA 或性能档位后，先用一个小任务验证。