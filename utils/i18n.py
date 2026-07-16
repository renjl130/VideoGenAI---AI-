"""
国际化模块 - 支持中文/英文切换
"""

# 语言包
TRANSLATIONS = {
    "zh_CN": {
        # 应用信息
        "app_name": "VideoGenAI",
        "app_title": "VideoGenAI - 本地AI视频生成软件",
        "app_version": "版本: 1.0.0",
        
        # 启动信息
        "check_deps": "检查依赖...",
        "deps_ok": "依赖检查通过",
        "check_gpu": "检查GPU...",
        "gpu_detected": "检测到GPU: {name}",
        "gpu_vram": "显存: {size:.1f} GB",
        "gpu_not_found": "警告: 未检测到CUDA GPU，将使用CPU（速度会很慢）",
        "setup_env": "设置环境...",
        "env_ok": "环境设置完成",
        "start_gui": "启动图形界面...",
        "gui_ok": "图形界面已启动",
        "start_failed": "启动失败: {error}",
        
        # GPU状态
        "gpu_status": "GPU 状态",
        "detecting": "检测中...",
        "no_gpu": "未检测到GPU",
        "vram": "显存",
        "temperature": "温度",
        "utilization": "利用率",
        "power": "功耗",
        
        # 模型选择
        "model_selection": "模型选择",
        "select_model": "选择模型",
        "model_info": "模型信息",
        "load_model": "加载模型",
        "unload_model": "卸载模型",
        "download_model": "下载模型",
        "model_loaded": "模型已加载",
        "model_unloaded": "模型已卸载",
        "loading": "加载中...",
        "unloading": "卸载中...",
        
        # Prompt
        "prompt": "提示词",
        "prompt_placeholder": "描述你想要生成的视频...",
        "negative_prompt": "负面提示词",
        "negative_placeholder": "描述你想避免的内容（可选）...",
        "prompt_history": "历史提示词",
        "refresh": "刷新",
        
        # 参数设置
        "generation_params": "生成参数",
        "resolution": "分辨率",
        "width": "宽度",
        "height": "高度",
        "preset": "预设",
        "custom": "自定义",
        "video_settings": "视频设置",
        "frames": "帧数",
        "fps": "帧率",
        "duration": "时长",
        "seconds": "秒",
        "generation_settings": "生成设置",
        "steps": "步数",
        "cfg_scale": "引导强度",
        "seed": "种子",
        "random": "随机",
        "random_seed": "随机种子 (-1为随机)",
        "optimization": "优化选项",
        "cpu_offload": "CPU卸载 (低显存)",
        "vae_tiling": "VAE分块",
        "flash_attention": "闪速注意力",
        
        # 生成按钮
        "generate_video": "生成视频",
        "stop_generation": "停止生成",
        "open_output": "打开输出目录",
        
        # 任务
        "task_queue": "任务队列",
        "clear": "清除",
        "clear_completed": "清除已完成",
        "pending": "等待中",
        "running": "运行中",
        "completed": "已完成",
        "failed": "失败",
        "cancelled": "已取消",
        "queue_status": "队列: {pending} 等待 | {running} 运行 | {completed} 完成",
        
        # 进度
        "progress": "进度",
        "generating": "生成中...",
        "generation_complete": "生成完成！",
        "generation_failed": "生成失败: {error}",
        
        # 日志
        "log_output": "日志输出",
        
        # 历史
        "history": "历史记录",
        "refresh_history": "刷新",
        "clear_history": "清空历史",
        "confirm_clear_history": "确定要清空所有历史记录吗？",
        
        # 菜单
        "file": "文件",
        "model": "模型",
        "tools": "工具",
        "help": "帮助",
        "exit": "退出",
        "clear_cache": "清除缓存",
        "about": "关于",
        "settings": "设置",
        "language": "语言",
        
        # 关于
        "about_title": "关于 VideoGenAI",
        "about_text": "<h2>VideoGenAI v1.0.0</h2><p>本地AI视频生成软件</p><p>基于 Wan2.1 开源模型</p><p>100%本地运行，无需联网</p><p>许可证: Apache 2.0</p>",
        
        # 对话框
        "confirm": "确认",
        "confirm_exit": "确定要退出吗？",
        "success": "成功",
        "error": "错误",
        "warning": "警告",
        "info": "信息",
        "yes": "是",
        "no": "否",
        "ok": "确定",
        "cancel": "取消",
        
        # 模型信息
        "type": "类型",
        "license": "许可证",
        "vram_required": "显存需求",
        
        # 状态
        "ready": "就绪",
        "task_submitted": "任务已提交: {id}",
        "task_completed": "任务完成: {id}",
        "task_failed": "任务失败: {error}",
        "task_cancelled": "任务已取消: {id}",
        "cache_cleared": "缓存已清除",
        
        # 下载
        "confirm_download": "确定要下载模型 {model} 吗？",
        "download_started": "下载已开始",
        "download_failed": "下载失败",
        
        # LoRA
        "lora": "LoRA",
        "none": "无",
        "strength": "强度",
    },
    
    "en_US": {
        # App info
        "app_name": "VideoGenAI",
        "app_title": "VideoGenAI - Local AI Video Generation",
        "app_version": "Version: 1.0.0",
        
        # Startup
        "check_deps": "Checking dependencies...",
        "deps_ok": "Dependencies check passed",
        "check_gpu": "Checking GPU...",
        "gpu_detected": "GPU detected: {name}",
        "gpu_vram": "VRAM: {size:.1f} GB",
        "gpu_not_found": "Warning: No CUDA GPU detected, using CPU (will be slow)",
        "setup_env": "Setting up environment...",
        "env_ok": "Environment setup complete",
        "start_gui": "Starting GUI...",
        "gui_ok": "GUI started successfully",
        "start_failed": "Startup failed: {error}",
        
        # GPU Status
        "gpu_status": "GPU Status",
        "detecting": "Detecting...",
        "no_gpu": "No GPU Detected",
        "vram": "VRAM",
        "temperature": "Temperature",
        "utilization": "Utilization",
        "power": "Power",
        
        # Model Selection
        "model_selection": "Model Selection",
        "select_model": "Select Model",
        "model_info": "Model Info",
        "load_model": "Load Model",
        "unload_model": "Unload Model",
        "download_model": "Download Model",
        "model_loaded": "Model Loaded",
        "model_unloaded": "Model Unloaded",
        "loading": "Loading...",
        "unloading": "Unloading...",
        
        # Prompt
        "prompt": "Prompt",
        "prompt_placeholder": "Describe the video you want to generate...",
        "negative_prompt": "Negative Prompt",
        "negative_placeholder": "What to avoid in the video (optional)...",
        "prompt_history": "Prompt History",
        "refresh": "Refresh",
        
        # Parameters
        "generation_params": "Generation Parameters",
        "resolution": "Resolution",
        "width": "Width",
        "height": "Height",
        "preset": "Preset",
        "custom": "Custom",
        "video_settings": "Video Settings",
        "frames": "Frames",
        "fps": "FPS",
        "duration": "Duration",
        "seconds": "sec",
        "generation_settings": "Generation Settings",
        "steps": "Steps",
        "cfg_scale": "CFG Scale",
        "seed": "Seed",
        "random": "Random",
        "random_seed": "Seed (-1 for random)",
        "optimization": "Optimization",
        "cpu_offload": "CPU Offload (Low VRAM)",
        "vae_tiling": "VAE Tiling",
        "flash_attention": "Flash Attention",
        
        # Generate buttons
        "generate_video": "Generate Video",
        "stop_generation": "Stop Generation",
        "open_output": "Open Output Folder",
        
        # Tasks
        "task_queue": "Task Queue",
        "clear": "Clear",
        "clear_completed": "Clear Completed",
        "pending": "Pending",
        "running": "Running",
        "completed": "Completed",
        "failed": "Failed",
        "cancelled": "Cancelled",
        "queue_status": "Queue: {pending} pending | {running} running | {completed} completed",
        
        # Progress
        "progress": "Progress",
        "generating": "Generating...",
        "generation_complete": "Generation Complete!",
        "generation_failed": "Generation Failed: {error}",
        
        # Log
        "log_output": "Log Output",
        
        # History
        "history": "History",
        "refresh_history": "Refresh",
        "clear_history": "Clear All",
        "confirm_clear_history": "Are you sure you want to clear all history?",
        
        # Menu
        "file": "File",
        "model": "Model",
        "tools": "Tools",
        "help": "Help",
        "exit": "Exit",
        "clear_cache": "Clear Cache",
        "about": "About",
        "settings": "Settings",
        "language": "Language",
        
        # About
        "about_title": "About VideoGenAI",
        "about_text": "<h2>VideoGenAI v1.0.0</h2><p>Local AI Video Generation Software</p><p>Based on Wan2.1 Open Source Model</p><p>100% Local - No Internet Required</p><p>License: Apache 2.0</p>",
        
        # Dialogs
        "confirm": "Confirm",
        "confirm_exit": "Are you sure you want to exit?",
        "success": "Success",
        "error": "Error",
        "warning": "Warning",
        "info": "Info",
        "yes": "Yes",
        "no": "No",
        "ok": "OK",
        "cancel": "Cancel",
        
        # Model info
        "type": "Type",
        "license": "License",
        "vram_required": "VRAM Required",
        
        # Status
        "ready": "Ready",
        "task_submitted": "Task submitted: {id}",
        "task_completed": "Task completed: {id}",
        "task_failed": "Task failed: {error}",
        "task_cancelled": "Task cancelled: {id}",
        "cache_cleared": "Cache cleared",
        
        # Download
        "confirm_download": "Download model {model}?",
        "download_started": "Download started",
        "download_failed": "Download failed",
        
        # LoRA
        "lora": "LoRA",
        "none": "None",
        "strength": "Strength",
    }
}


class I18n:
    """国际化管理器"""
    
    _instance = None
    _current_lang = "zh_CN"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def set_language(cls, lang: str):
        """设置语言"""
        if lang in TRANSLATIONS:
            cls._current_lang = lang
            return True
        return False
    
    @classmethod
    def get_language(cls) -> str:
        """获取当前语言"""
        return cls._current_lang
    
    @classmethod
    def t(cls, key: str, **kwargs) -> str:
        """翻译"""
        lang = TRANSLATIONS.get(cls._current_lang, {})
        text = lang.get(key, key)
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except:
                pass
        
        return text
    
    @classmethod
    def get_available_languages(cls) -> dict:
        """获取可用语言"""
        return {
            "zh_CN": "中文",
            "en_US": "English"
        }


# 便捷翻译函数
def t(key: str, **kwargs) -> str:
    """翻译快捷方式"""
    return I18n.t(key, **kwargs)
