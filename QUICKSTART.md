# VideoGenAI 快速开始指南

## 一分钟快速上手

### Windows用户

1. **下载项目**
   - 下载整个项目文件夹到本地

2. **双击启动**
   - 双击 `启动.bat` 文件
   - 首次运行会自动安装依赖（需要几分钟）

3. **开始使用**
   - 等待程序启动
   - 选择模型
   - 输入Prompt
   - 点击"生成视频"

### 详细步骤

#### 第一步：环境准备

确保已安装Python 3.10+：
```bash
python --version
```

如果未安装，请从 https://www.python.org/downloads/ 下载安装。

#### 第二步：启动程序

**方法一：使用启动脚本（推荐）**
- 双击 `启动.bat`

**方法二：命令行启动**
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 启动程序
python main.py
```

#### 第三步：首次使用

1. **等待模型下载**
   - 首次启动会自动下载模型
   - 模型大小约5GB
   - 请确保网络畅通

2. **选择模型**
   - 在左侧面板选择模型
   - 推荐初学者使用 `wan2.1-t2v-1.3b`（显存需求最低）

3. **输入Prompt**
   - 在Prompt输入框描述你想要的视频
   - 例如：`A cat playing with a ball of yarn`

4. **调整参数**
   - 分辨率：480P（默认）或720P
   - 帧数：81（约5秒视频）
   - 步数：50（质量与速度的平衡）

5. **生成视频**
   - 点击"生成视频"按钮
   - 等待生成完成
   - 视频自动保存到 `outputs` 目录

## 常见问题

### Q: 显存不足怎么办？

A: 尝试以下方法：
1. 使用1.3B模型（显存需求最低8GB）
2. 勾选"CPU Offload"选项
3. 降低分辨率到480P
4. 减少帧数

### Q: 生成速度很慢？

A: 可以尝试：
1. 使用更少的步数（如30步）
2. 降低分辨率
3. 使用更小的模型

### Q: 如何使用国内镜像？

A: 安装时使用清华镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 模型下载失败？

A: 可以：
1. 检查网络连接
2. 使用VPN或代理
3. 手动下载模型放到 `models` 目录

## 系统要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 | Windows 11 |
| Python | 3.10 | 3.11+ |
| GPU | GTX 1060 6GB | RTX 3060 12GB+ |
| 显存 | 8GB | 24GB |
| 内存 | 16GB | 32GB |
| 硬盘 | 50GB | 100GB+ |

## 获取帮助

- 查看 `README.md` 获取详细文档
- 查看 `logs` 目录获取运行日志
- 提交Issue反馈问题

## 下一步

- 尝试不同的Prompt和参数
- 探索LoRA和ControlNet功能
- 查看历史记录和Prompt库
- 自定义配置文件
