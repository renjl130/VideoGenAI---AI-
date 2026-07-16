"""
后端引擎管理器 - 整合所有后端功能
"""
import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from utils.config_manager import get_config, ConfigManager
from utils.logger import get_logger
from utils.gpu_monitor import get_gpu_monitor, GPUInfo
from utils.model_downloader import get_model_downloader, ModelDownloader, ModelInfo
from utils.task_queue import get_task_queue, TaskQueue, GenerationTask, TaskStatus, TaskType
from utils.history_manager import get_history_manager, HistoryManager, HistoryRecord
from engines.wan_engine import WanEngine, get_engine_manager, EngineManager
from engines.base_engine import GenerationParams, GenerationResult

logger = get_logger("backend")


class BackendManager:
    """后端管理器 - 协调所有后端功能"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化后端管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        
        # 初始化各个管理器
        self._config = get_config()
        self._gpu_monitor = get_gpu_monitor()
        self._model_downloader = get_model_downloader(self._config.models.models_dir)
        self._task_queue = get_task_queue(self._config.queue.max_concurrent)
        self._history_manager = get_history_manager()
        self._engine_manager = get_engine_manager()
        
        # 设置任务执行函数
        self._task_queue.set_execute_function(self._execute_generation_task)
        
        # 注册回调
        self._setup_callbacks()
        
        # 启动GPU监控
        self._gpu_monitor.start_monitoring(interval=2.0)
        
        logger.info("后端管理器初始化完成")
    
    def _setup_callbacks(self):
        """设置回调函数"""
        # 任务队列回调
        self._task_queue.on_task_complete(self._on_task_complete)
        self._task_queue.on_task_fail(self._on_task_fail)
        
        # 下载回调
        self._model_downloader.add_callback(self._on_download_complete)
    
    def _execute_generation_task(self, task: GenerationTask) -> Dict[str, Any]:
        """执行视频生成任务"""
        logger.info(f"开始执行任务: {task.task_id}")
        
        # 获取引擎
        engine = self._engine_manager.get_active_engine()
        if not engine:
            raise RuntimeError("没有活跃的引擎")
        
        # 构建生成参数
        params = GenerationParams(
            prompt=task.prompt,
            negative_prompt=task.negative_prompt,
            width=task.width,
            height=task.height,
            num_frames=task.num_frames,
            fps=task.fps,
            steps=task.steps,
            cfg_scale=task.cfg_scale,
            seed=task.seed,
            image_path=task.image_path,
            video_path=task.video_path,
            precision=task.precision,
            cpu_offload=task.cpu_offload,
            vae_tiling=task.vae_tiling,
            progress_callback=lambda p, m: self._task_queue.update_progress(task.task_id, p)
        )
        
        # 执行生成
        result = engine.generate(params)
        
        if not result.success:
            raise RuntimeError(result.error_message)
        
        return {
            "output_path": result.output_path,
            "duration": result.duration,
            "seed_used": result.seed_used
        }
    
    def _on_task_complete(self, task: GenerationTask):
        """任务完成回调"""
        logger.info(f"任务完成: {task.task_id}")
        
        # 保存历史记录
        if self._config.output.auto_save_history:
            record = HistoryRecord(
                record_id=task.task_id,
                task_type=task.task_type.value,
                model_id=task.model_id,
                prompt=task.prompt,
                negative_prompt=task.negative_prompt,
                parameters=task.to_dict(),
                output_path=task.output_path or "",
                created_at=task.created_at.isoformat(),
                duration=(task.completed_at - task.started_at).total_seconds() if task.completed_at and task.started_at else 0,
                file_size=os.path.getsize(task.output_path) if task.output_path and os.path.exists(task.output_path) else 0
            )
            self._history_manager.add_record(record)
    
    def _on_task_fail(self, task: GenerationTask):
        """任务失败回调"""
        logger.error(f"任务失败: {task.task_id}, 错误: {task.error_message}")
    
    def _on_download_complete(self, model_id: str, progress):
        """下载完成回调"""
        if progress.status == "completed":
            logger.info(f"模型下载完成: {model_id}")
    
    # ========== 公共接口 ==========
    
    def get_config(self) -> ConfigManager:
        """获取配置管理器"""
        return self._config
    
    def get_gpu_monitor(self):
        """获取GPU监控器"""
        return self._gpu_monitor
    
    def get_model_downloader(self) -> ModelDownloader:
        """获取模型下载管理器"""
        return self._model_downloader
    
    def get_task_queue(self) -> TaskQueue:
        """获取任务队列"""
        return self._task_queue
    
    def get_history_manager(self) -> HistoryManager:
        """获取历史记录管理器"""
        return self._history_manager
    
    def get_engine_manager(self) -> EngineManager:
        """获取引擎管理器"""
        return self._engine_manager
    
    def get_gpu_info(self) -> List[GPUInfo]:
        """获取GPU信息"""
        return self._gpu_monitor.get_all_gpu_info()
    
    def get_downloaded_models(self) -> Dict[str, ModelInfo]:
        """获取已下载的模型"""
        return self._model_downloader.get_downloaded_models()
    
    def get_available_models(self) -> Dict[str, ModelInfo]:
        """获取可用模型"""
        return self._model_downloader.get_available_models()
    
    def download_model(self, model_id: str) -> bool:
        """下载模型"""
        return self._model_downloader.download_model(model_id)
    
    def load_model(self, model_id: str, **kwargs) -> bool:
        """加载模型"""
        model_path = self._model_downloader.get_model_path(model_id)
        if not model_path:
            # 尝试下载
            if self._config.models.auto_download:
                logger.info(f"模型未找到，开始下载: {model_id}")
                if not self.download_model(model_id):
                    return False
                # 等待下载完成
                # 这里简化处理，实际应该等待下载完成
                return False
            else:
                logger.error(f"模型未下载: {model_id}")
                return False
        
        return self._engine_manager.load_model(model_id, str(model_path), **kwargs)
    
    def unload_model(self):
        """卸载当前模型"""
        engine = self._engine_manager.get_active_engine()
        if engine:
            engine.unload_model()
    
    def submit_task(self, 
                    task_type: TaskType,
                    prompt: str,
                    negative_prompt: str = "",
                    **kwargs) -> str:
        """提交生成任务"""
        # 创建任务
        task = GenerationTask(
            task_type=task_type,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model_id=kwargs.get("model_id", self._config.models.default_model),
            width=kwargs.get("width", 832),
            height=kwargs.get("height", 480),
            num_frames=kwargs.get("num_frames", 81),
            fps=kwargs.get("fps", 16),
            steps=kwargs.get("steps", 50),
            cfg_scale=kwargs.get("cfg_scale", 5.0),
            seed=kwargs.get("seed", -1),
            image_path=kwargs.get("image_path"),
            video_path=kwargs.get("video_path"),
            precision=kwargs.get("precision", "auto"),
            cpu_offload=kwargs.get("cpu_offload", False),
            vae_tiling=kwargs.get("vae_tiling", True)
        )
        
        # 保存Prompt历史
        if self._config.output.auto_save_prompt:
            self._history_manager.add_prompt(prompt, task.model_id, task_type.value)
        
        # 提交任务
        task_id = self._task_queue.add_task(task)
        logger.info(f"提交任务: {task_id}")
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self._task_queue.cancel_task(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self._task_queue.get_task(task_id)
        if task:
            return task.to_dict()
        return None
    
    def get_queue_status(self) -> Dict[str, int]:
        """获取队列状态"""
        return self._task_queue.get_queue_status()
    
    def get_history(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取历史记录"""
        records = self._history_manager.get_history(limit, offset)
        return [r.to_dict() for r in records]
    
    def get_prompt_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取Prompt历史"""
        return self._history_manager.get_prompts(limit)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._history_manager.get_statistics()
    
    def clear_cache(self):
        """清除缓存"""
        self._gpu_monitor.clear_cache()
        self._task_queue.clear_completed()
    
    def shutdown(self):
        """关闭后端"""
        logger.info("关闭后端管理器...")
        
        # 停止GPU监控
        self._gpu_monitor.stop_monitoring()
        
        # 卸载模型
        self.unload_model()
        
        logger.info("后端管理器已关闭")


# 全局后端管理器实例
_backend_manager = None


def get_backend_manager() -> BackendManager:
    """获取后端管理器实例"""
    global _backend_manager
    if _backend_manager is None:
        _backend_manager = BackendManager()
    return _backend_manager
