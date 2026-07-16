# ruff: noqa: E501, W293
"""
截图脚本 - 捕获UI界面截图
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def capture_screenshots():
    """捕获UI截图"""
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        from ui.main_window import MainWindow

        # 创建应用
        app = QApplication(sys.argv)

        # 创建主窗口
        window = MainWindow()
        window.show()

        # 确保截图目录存在
        screenshots_dir = project_root / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)

        def take_screenshot():
            """截图函数"""
            # 截取整个窗口
            pixmap = window.grab()

            # 保存截图
            screenshot_path = screenshots_dir / "main_window.png"
            pixmap.save(str(screenshot_path))
            print(f"Screenshot saved: {screenshot_path}")

            # 截取左侧面板
            left_panel = window.findChild(type(window), "left_panel")
            if left_panel:
                left_pixmap = left_panel.grab()
                left_path = screenshots_dir / "left_panel.png"
                left_pixmap.save(str(left_path))
                print(f"Left panel saved: {left_path}")

            # 截取右侧面板
            right_panel = window.findChild(type(window), "right_panel")
            if right_panel:
                right_pixmap = right_panel.grab()
                right_path = screenshots_dir / "right_panel.png"
                right_pixmap.save(str(right_path))
                print(f"Right panel saved: {right_path}")

            # 退出应用
            app.quit()

        # 延迟截图，确保UI完全加载
        QTimer.singleShot(1000, take_screenshot)

        # 运行应用
        app.exec()

        return True

    except Exception as e:
        print(f"Error capturing screenshots: {e}")
        return False


def create_demo_screenshots():
    """创建演示截图（如果无法运行GUI）"""
    screenshots_dir = project_root / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    # 创建一个简单的HTML预览
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VideoGenAI - UI Preview</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            gap: 20px;
        }
        .left-panel {
            width: 400px;
            background: #1a1a2e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
        }
        .right-panel {
            flex: 1;
            background: #1a1a2e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
        }
        .card {
            background: #16162a;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 16px;
            border: 1px solid #2a2a4a;
        }
        .title {
            color: #7c8aff;
            font-size: 24px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 20px;
            background: linear-gradient(90deg, #7c8aff, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .section-title {
            color: #7c8aff;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .input {
            background: #0f0f1a;
            border: 2px solid #2a2a4a;
            border-radius: 8px;
            padding: 10px;
            color: #e0e0e0;
            width: 100%;
            box-sizing: border-box;
            margin-bottom: 10px;
        }
        .input:focus {
            border-color: #7c8aff;
        }
        .btn {
            background: linear-gradient(90deg, #10b981, #059669);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            margin-bottom: 10px;
        }
        .btn:hover {
            background: linear-gradient(90deg, #34d399, #10b981);
        }
        .btn-secondary {
            background: #2a2a3e;
            border: 1px solid #3a3a5e;
        }
        .btn-danger {
            background: linear-gradient(90deg, #ef4444, #dc2626);
        }
        .gpu-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .gpu-stat {
            background: #0f0f1a;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
        }
        .gpu-stat-value {
            color: #7c8aff;
            font-size: 18px;
            font-weight: 600;
        }
        .gpu-stat-label {
            color: #888;
            font-size: 12px;
        }
        .progress-bar {
            background: #16162a;
            border-radius: 8px;
            height: 20px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            background: linear-gradient(90deg, #4f46e5, #7c3aed);
            height: 100%;
            width: 65%;
            border-radius: 8px;
        }
        .tab {
            display: inline-block;
            padding: 10px 20px;
            background: #16162a;
            border: 1px solid #2a2a4a;
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            margin-right: 5px;
            color: #888;
        }
        .tab.active {
            background: #1a1a2e;
            color: #7c8aff;
            border-bottom: 2px solid #7c8aff;
        }
        .task-item {
            background: #16162a;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid #10b981;
        }
        .log-line {
            font-family: 'Consolas', monospace;
            font-size: 12px;
            margin-bottom: 4px;
        }
        .log-time { color: #6b7280; }
        .log-level { font-weight: 600; }
        .log-info { color: #e0e0e0; }
        .log-warning { color: #fbbf24; }
        .log-error { color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Left Panel -->
        <div class="left-panel">
            <div class="title">VideoGenAI</div>
            
            <!-- GPU Status -->
            <div class="card">
                <div class="section-title">GPU Status</div>
                <div style="font-weight: 600; margin-bottom: 10px;">NVIDIA RTX 4090</div>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <div style="color: #888; font-size: 12px;">12.5 / 24 GB (52%)</div>
                <div class="gpu-info">
                    <div class="gpu-stat">
                        <div class="gpu-stat-value">65°C</div>
                        <div class="gpu-stat-label">Temperature</div>
                    </div>
                    <div class="gpu-stat">
                        <div class="gpu-stat-value">78%</div>
                        <div class="gpu-stat-label">Utilization</div>
                    </div>
                </div>
            </div>
            
            <!-- Model Selection -->
            <div class="card">
                <div class="section-title">Model Selection</div>
                <select class="input">
                    <option>[Ready] Wan2.1 T2V 1.3B - Text to Video</option>
                    <option>[Download] Wan2.1 T2V 14B - High Quality</option>
                    <option>[Download] Wan2.1 I2V 14B - Image to Video</option>
                </select>
                <div style="color: #888; font-size: 12px; margin-bottom: 10px;">
                    Type: t2v | Resolution: 480p<br>
                    VRAM: 8 GB | License: Apache 2.0
                </div>
                <button class="btn">Load Model</button>
                <button class="btn btn-secondary">Download Model</button>
            </div>
            
            <!-- Prompt -->
            <div class="card">
                <div class="section-title">Prompt</div>
                <textarea class="input" rows="3" placeholder="Describe the video you want to generate...">A beautiful sunset over the ocean, waves gently lapping at the shore, golden light reflecting on the water</textarea>
                
                <div class="section-title" style="color: #f87171;">Negative Prompt</div>
                <textarea class="input" rows="2" placeholder="What to avoid...">blurry, low quality, distorted</textarea>
            </div>
            
            <!-- Parameters -->
            <div class="card">
                <div class="section-title">Generation Parameters</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div>
                        <label style="color: #888; font-size: 12px;">Width</label>
                        <input class="input" type="number" value="832">
                    </div>
                    <div>
                        <label style="color: #888; font-size: 12px;">Height</label>
                        <input class="input" type="number" value="480">
                    </div>
                    <div>
                        <label style="color: #888; font-size: 12px;">Frames</label>
                        <input class="input" type="number" value="81">
                    </div>
                    <div>
                        <label style="color: #888; font-size: 12px;">FPS</label>
                        <input class="input" type="number" value="16">
                    </div>
                    <div>
                        <label style="color: #888; font-size: 12px;">Steps</label>
                        <input class="input" type="number" value="50">
                    </div>
                    <div>
                        <label style="color: #888; font-size: 12px;">CFG Scale</label>
                        <input class="input" type="number" value="5.0">
                    </div>
                </div>
                <div style="margin-top: 10px;">
                    <label style="color: #888; font-size: 12px;">Seed (-1 for random)</label>
                    <input class="input" type="number" value="-1">
                </div>
            </div>
            
            <!-- Generate Button -->
            <button class="btn" style="font-size: 18px; padding: 16px;">Generate Video</button>
            <button class="btn btn-danger">Stop Generation</button>
            <button class="btn btn-secondary">Open Output Folder</button>
        </div>
        
        <!-- Right Panel -->
        <div class="right-panel">
            <!-- Tabs -->
            <div>
                <span class="tab active">Tasks</span>
                <span class="tab">Logs</span>
                <span class="tab">History</span>
            </div>
            
            <!-- Content -->
            <div style="background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 0 8px 8px 8px; padding: 20px; min-height: 600px;">
                <!-- Progress -->
                <div class="card">
                    <div class="section-title">Generation Progress</div>
                    <div class="progress-bar" style="height: 24px;">
                        <div class="progress-fill" style="width: 65%;"></div>
                    </div>
                    <div style="text-align: center; color: #7c8aff; font-weight: 600;">Progress: 65%</div>
                </div>
                
                <!-- Task List -->
                <div class="card">
                    <div class="section-title">Task Queue</div>
                    <div class="task-item">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #10b981; font-weight: 600;">[DONE]</span>
                            <span style="color: #888;">2024-01-15 14:30</span>
                        </div>
                        <div>A beautiful sunset over the ocean...</div>
                    </div>
                    <div class="task-item" style="border-left-color: #7c8aff;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #7c8aff; font-weight: 600;">[RUN]</span>
                            <span style="color: #888;">65%</span>
                        </div>
                        <div>A cat playing with a ball of yarn...</div>
                    </div>
                    <div class="task-item" style="border-left-color: #fbbf24;">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #fbbf24; font-weight: 600;">[WAIT]</span>
                            <span style="color: #888;">Pending</span>
                        </div>
                        <div>A futuristic city at night...</div>
                    </div>
                </div>
                
                <!-- Log Output -->
                <div class="card">
                    <div class="section-title">Log Output</div>
                    <div style="background: #0a0a1a; padding: 12px; border-radius: 6px; font-family: 'Consolas', monospace; font-size: 12px;">
                        <div class="log-line">
                            <span class="log-time">[14:30:15]</span>
                            <span class="log-level log-info">[INFO]</span>
                            <span class="log-info">Model loaded successfully</span>
                        </div>
                        <div class="log-line">
                            <span class="log-time">[14:30:16]</span>
                            <span class="log-level log-info">[INFO]</span>
                            <span class="log-info">Task submitted: a1b2c3d4</span>
                        </div>
                        <div class="log-line">
                            <span class="log-time">[14:30:17]</span>
                            <span class="log-level log-info">[INFO]</span>
                            <span class="log-info">Starting video generation...</span>
                        </div>
                        <div class="log-line">
                            <span class="log-time">[14:30:45]</span>
                            <span class="log-level log-warning">[WARN]</span>
                            <span class="log-warning">VRAM usage at 85%</span>
                        </div>
                        <div class="log-line">
                            <span class="log-time">[14:31:02]</span>
                            <span class="log-level log-info">[INFO]</span>
                            <span class="log-info">Step 25/50 completed</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

    html_path = screenshots_dir / "ui_preview.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"UI preview created: {html_path}")
    return True


def main():
    print("=" * 60)
    print("  VideoGenAI Screenshot Capture")
    print("=" * 60)

    # 尝试捕获真实截图
    print("\nAttempting to capture real screenshots...")
    if capture_screenshots():
        print("Real screenshots captured successfully!")
        return 0

    # 如果失败，创建演示截图
    print("\nCreating demo UI preview...")
    if create_demo_screenshots():
        print("Demo preview created successfully!")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
