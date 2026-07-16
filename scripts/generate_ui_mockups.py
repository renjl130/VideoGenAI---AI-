"""
UI Mockup Generator - 使用Pillow生成UI截图
"""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

project_root = Path(__file__).parent.parent


def create_gradient(width, height, color1, color2):
    """创建渐变背景"""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    for y in range(height):
        r = int(color1[0] + (color2[0] - color1[0]) * y / height)
        g = int(color1[1] + (color2[1] - color1[1]) * y / height)
        b = int(color1[2] + (color2[2] - color1[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return img


def draw_rounded_rect(draw, bbox, radius, fill, outline=None):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline)


def create_main_window_mockup():
    """创建主窗口模拟图"""
    width, height = 1600, 1000
    img = create_gradient(width, height, (15, 15, 15), (10, 10, 20))
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_medium = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 左侧面板背景
    draw_rounded_rect(draw, (20, 20, 420, 980), 12, (26, 26, 46), (42, 42, 74))
    
    # Logo
    draw.text((160, 40), "VideoGenAI", fill=(124, 138, 255), font=font_large)
    
    # GPU状态卡片
    draw_rounded_rect(draw, (30, 80, 410, 200), 10, (22, 22, 42), (42, 42, 74))
    draw.text((40, 90), "GPU Status", fill=(124, 138, 255), font=font_medium)
    draw.text((40, 110), "NVIDIA RTX 4090", fill=(224, 224, 224), font=font_medium)
    
    # 进度条
    draw_rounded_rect(draw, (40, 140, 400, 155), 8, (22, 22, 42))
    draw_rounded_rect(draw, (40, 140, 270, 155), 8, (79, 70, 229))
    draw.text((40, 160), "12.5 / 24 GB (52%)", fill=(136, 136, 136), font=font_small)
    
    # GPU统计
    draw_rounded_rect(draw, (40, 180, 220, 200), 6, (15, 15, 26))
    draw.text((100, 185), "65°C", fill=(124, 138, 255), font=font_medium)
    
    draw_rounded_rect(draw, (230, 180, 400, 200), 6, (15, 15, 26))
    draw.text((290, 185), "78%", fill=(124, 138, 255), font=font_medium)
    
    # 模型选择卡片
    draw_rounded_rect(draw, (30, 220, 410, 370), 10, (22, 22, 42), (42, 42, 74))
    draw.text((40, 230), "Model Selection", fill=(124, 138, 255), font=font_medium)
    
    # 下拉框
    draw_rounded_rect(draw, (40, 260, 400, 290), 8, (22, 22, 50), (42, 42, 74))
    draw.text((50, 268), "[Ready] Wan2.1 T2V 1.3B", fill=(224, 224, 224), font=font_small)
    
    # 模型信息
    draw.text((40, 300), "Type: t2v | Resolution: 480p", fill=(136, 136, 136), font=font_small)
    draw.text((40, 315), "VRAM: 8 GB | License: Apache 2.0", fill=(136, 136, 136), font=font_small)
    
    # 按钮
    draw_rounded_rect(draw, (40, 340, 200, 365), 8, (16, 185, 129))
    draw.text((80, 345), "Load Model", fill=(255, 255, 255), font=font_small)
    
    draw_rounded_rect(draw, (210, 340, 400, 365), 8, (42, 42, 62), (58, 58, 94))
    draw.text((270, 345), "Download", fill=(224, 224, 224), font=font_small)
    
    # Prompt卡片
    draw_rounded_rect(draw, (30, 390, 410, 530), 10, (22, 22, 42), (42, 42, 74))
    draw.text((40, 400), "Prompt", fill=(124, 138, 255), font=font_medium)
    
    # 输入框
    draw_rounded_rect(draw, (40, 425, 400, 490), 8, (15, 15, 30), (42, 42, 74))
    draw.text((50, 435), "A beautiful sunset over the ocean,", fill=(224, 224, 224), font=font_small)
    draw.text((50, 450), "waves gently lapping at the shore...", fill=(224, 224, 224), font=font_small)
    
    draw.text((40, 500), "Negative Prompt", fill=(248, 113, 113), font=font_medium)
    draw_rounded_rect(draw, (40, 520, 400, 550), 8, (15, 15, 30), (42, 42, 74))
    
    # 参数卡片
    draw_rounded_rect(draw, (30, 570, 410, 780), 10, (22, 22, 42), (42, 42, 74))
    draw.text((40, 580), "Generation Parameters", fill=(124, 138, 255), font=font_medium)
    
    # 参数网格
    params = [
        ("Width", "832", 40, 610),
        ("Height", "480", 220, 610),
        ("Frames", "81", 40, 660),
        ("FPS", "16", 220, 660),
        ("Steps", "50", 40, 710),
        ("CFG Scale", "5.0", 220, 710),
    ]
    
    for label, value, x, y in params:
        draw.text((x, y), label, fill=(136, 136, 136), font=font_small)
        draw_rounded_rect(draw, (x, y + 15, x + 160, y + 40), 6, (15, 15, 30), (42, 42, 74))
        draw.text((x + 10, y + 20), value, fill=(224, 224, 224), font=font_small)
    
    # 生成按钮
    draw_rounded_rect(draw, (30, 800, 410, 845), 10, (16, 185, 129))
    draw.text((150, 815), "Generate Video", fill=(255, 255, 255), font=font_large)
    
    # 停止按钮
    draw_rounded_rect(draw, (30, 860, 410, 900), 8, (239, 68, 68))
    draw.text((160, 870), "Stop Generation", fill=(255, 255, 255), font=font_medium)
    
    # 打开目录按钮
    draw_rounded_rect(draw, (30, 915, 410, 955), 8, (42, 42, 62), (58, 58, 94))
    draw.text((130, 925), "Open Output Folder", fill=(224, 224, 224), font=font_medium)
    
    # 右侧面板
    draw_rounded_rect(draw, (440, 20, 1580, 980), 12, (26, 26, 46), (42, 42, 74))
    
    # 标签页
    tabs = [("Tasks", True), ("Logs", False), ("History", False)]
    x_offset = 460
    for tab_name, active in tabs:
        tab_width = len(tab_name) * 10 + 40
        if active:
            draw_rounded_rect(draw, (x_offset, 30, x_offset + tab_width, 55), 8, (26, 26, 46), (124, 138, 255))
            draw.text((x_offset + 20, 35), tab_name, fill=(124, 138, 255), font=font_medium)
        else:
            draw_rounded_rect(draw, (x_offset, 30, x_offset + tab_width, 55), 8, (22, 22, 42))
            draw.text((x_offset + 20, 35), tab_name, fill=(136, 136, 136), font=font_medium)
        x_offset += tab_width + 10
    
    # 进度卡片
    draw_rounded_rect(draw, (460, 70, 1560, 150), 10, (22, 22, 42), (42, 42, 74))
    draw.text((470, 80), "Generation Progress", fill=(124, 138, 255), font=font_medium)
    
    # 进度条
    draw_rounded_rect(draw, (470, 105, 1550, 125), 10, (22, 22, 42))
    draw_rounded_rect(draw, (470, 105, 1180, 125), 10, (79, 70, 229))
    draw.text((950, 108), "65%", fill=(255, 255, 255), font=font_small)
    
    # 任务列表卡片
    draw_rounded_rect(draw, (460, 170, 1560, 500), 10, (22, 22, 42), (42, 42, 74))
    draw.text((470, 180), "Task Queue", fill=(124, 138, 255), font=font_medium)
    
    # 任务项
    tasks = [
        ("[DONE]", "2024-01-15 14:30", "A beautiful sunset over the ocean...", (16, 185, 129)),
        ("[RUN]", "65%", "A cat playing with a ball of yarn...", (124, 138, 255)),
        ("[WAIT]", "Pending", "A futuristic city at night...", (251, 191, 36)),
    ]
    
    y_pos = 210
    for status, time, desc, color in tasks:
        draw_rounded_rect(draw, (470, y_pos, 1550, y_pos + 50), 6, (22, 22, 42))
        draw.line([(470, y_pos), (470, y_pos + 50)], fill=color, width=3)
        draw.text((480, y_pos + 5), status, fill=color, font=font_small)
        draw.text((550, y_pos + 5), time, fill=(136, 136, 136), font=font_small)
        draw.text((480, y_pos + 25), desc, fill=(224, 224, 224), font=font_small)
        y_pos += 60
    
    # 日志卡片
    draw_rounded_rect(draw, (460, 520, 1560, 960), 10, (22, 22, 42), (42, 42, 74))
    draw.text((470, 530), "Log Output", fill=(124, 138, 255), font=font_medium)
    
    # 日志内容
    draw_rounded_rect(draw, (470, 555, 1550, 950), 6, (10, 10, 26))
    
    logs = [
        ("[14:30:15]", "[INFO]", "Model loaded successfully", (224, 224, 224)),
        ("[14:30:16]", "[INFO]", "Task submitted: a1b2c3d4", (224, 224, 224)),
        ("[14:30:17]", "[INFO]", "Starting video generation...", (224, 224, 224)),
        ("[14:30:45]", "[WARN]", "VRAM usage at 85%", (251, 191, 36)),
        ("[14:31:02]", "[INFO]", "Step 25/50 completed", (224, 224, 224)),
        ("[14:31:30]", "[INFO]", "Step 33/50 completed", (224, 224, 224)),
    ]
    
    y_pos = 570
    for time, level, msg, color in logs:
        draw.text((480, y_pos), time, fill=(107, 114, 128), font=font_small)
        draw.text((560, y_pos), level, fill=color, font=font_small)
        draw.text((620, y_pos), msg, fill=color, font=font_small)
        y_pos += 20
    
    return img


def create_gpu_status_mockup():
    """创建GPU状态卡片模拟图"""
    img = Image.new('RGB', (380, 180), (22, 22, 42))
    draw = ImageDraw.Draw(img)
    
    try:
        font_medium = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.text((10, 10), "GPU Status", fill=(124, 138, 255), font=font_medium)
    draw.text((10, 35), "NVIDIA RTX 4090", fill=(224, 224, 224), font=font_medium)
    
    # 进度条
    draw.rounded_rectangle((10, 60, 370, 75), radius=8, fill=(15, 15, 26))
    draw.rounded_rectangle((10, 60, 200, 75), radius=8, fill=(79, 70, 229))
    draw.text((10, 80), "12.5 / 24 GB (52%)", fill=(136, 136, 136), font=font_small)
    
    # 统计
    draw.rounded_rectangle((10, 100, 180, 130), radius=6, fill=(15, 15, 26))
    draw.text((70, 108), "65°C", fill=(124, 138, 255), font=font_medium)
    
    draw.rounded_rectangle((200, 100, 370, 130), radius=6, fill=(15, 15, 26))
    draw.text((260, 108), "78%", fill=(124, 138, 255), font=font_medium)
    
    return img


def main():
    if not PIL_AVAILABLE:
        print("Pillow not available. Install with: pip install Pillow")
        print("Creating HTML preview instead...")
        
        # 运行HTML预览脚本
        import subprocess
        subprocess.run([sys.executable, str(project_root / "scripts" / "capture_screenshots.py")])
        return 0
    
    print("=" * 60)
    print("  UI Mockup Generator")
    print("=" * 60)
    
    screenshots_dir = project_root / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    
    # 创建主窗口模拟图
    print("\nGenerating main window mockup...")
    main_mockup = create_main_window_mockup()
    main_path = screenshots_dir / "main_window.png"
    main_mockup.save(str(main_path))
    print(f"Saved: {main_path}")
    
    # 创建GPU状态模拟图
    print("Generating GPU status mockup...")
    gpu_mockup = create_gpu_status_mockup()
    gpu_path = screenshots_dir / "gpu_status.png"
    gpu_mockup.save(str(gpu_path))
    print(f"Saved: {gpu_path}")
    
    print("\n" + "=" * 60)
    print("  Mockups generated successfully!")
    print("=" * 60)
    print(f"\nScreenshots saved to: {screenshots_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
