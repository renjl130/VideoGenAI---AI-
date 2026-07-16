"""
任务队列管理器 - 管理视频生成任务
"""
import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from utils.logger import get_logger

logger = get_logger("task_queue")


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待中
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消
    PAUSED = "paused"            # 已暂停


class TaskType(Enum):
    """任务类型枚举"""
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_CONTINUATION = "video_continuation"
    VIDEO_EXTENSION = "video_extension"


@dataclass
class GenerationTask:
    """视频生成任务"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: TaskType = TaskType.TEXT_TO_VIDEO
    status: TaskStatus = TaskStatus.PENDING
    
    # 生成参数
    model_id: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    
    # 视频参数
    width: int = 832
    height: int = 480
    num_frames: int = 81
    fps: int = 16
    steps: int = 50
    cfg_scale: float = 5.0
    seed: int = -1
    
    # 优化参数
    precision: str = "auto"
    cpu_offload: bool = False
    vae_tiling: bool = True
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 结果信息
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    
    # 历史记录
    prompt_history: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "model_id": self.model_id,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "fps": self.fps,
            "steps": self.steps,
            "cfg_scale": self.cfg_scale,
            "seed": self.seed,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "progress": self.progress
        }


class TaskQueue:
    """任务队列"""
    
    _instance = None
    
    def __new__(cls, max_concurrent: int = 1):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, max_concurrent: int = 1):
        """初始化任务队列"""
        if self._initialized:
            return
            
        self._initialized = True
        self._max_concurrent = max_concurrent
        
        # 任务存储
        self._tasks: Dict[str, GenerationTask] = {}
        self._pending_queue: deque = deque()
        self._running_tasks: Dict[str, threading.Thread] = {}
        
        # 回调函数
        self._on_task_start: List[Callable] = []
        self._on_task_complete: List[Callable] = []
        self._on_task_fail: List[Callable] = []
        self._on_task_cancel: List[Callable] = []
        self._on_progress_update: List[Callable] = []
        
        # 执行函数
        self._execute_func: Optional[Callable] = None
        
        # 锁
        self._lock = threading.Lock()
        
        logger.info(f"任务队列初始化，最大并发数: {max_concurrent}")
    
    def set_execute_function(self, func: Callable):
        """设置任务执行函数"""
        self._execute_func = func
    
    def add_task(self, task: GenerationTask) -> str:
        """添加任务"""
        with self._lock:
            self._tasks[task.task_id] = task
            self._pending_queue.append(task.task_id)
            logger.info(f"添加任务: {task.task_id}, 类型: {task.task_type.value}")
            
            # 尝试执行任务
            self._try_execute_next()
            
            return task.task_id
    
    def _try_execute_next(self):
        """尝试执行下一个任务"""
        if len(self._running_tasks) >= self._max_concurrent:
            return
        
        if not self._pending_queue:
            return
        
        if self._execute_func is None:
            logger.warning("未设置执行函数")
            return
        
        # 获取下一个任务
        task_id = self._pending_queue.popleft()
        task = self._tasks[task_id]
        
        # 更新状态
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        # 在新线程中执行
        thread = threading.Thread(
            target=self._execute_task,
            args=(task,),
            daemon=True
        )
        self._running_tasks[task_id] = thread
        thread.start()
        
        # 通知回调
        for callback in self._on_task_start:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
        
        logger.info(f"开始执行任务: {task_id}")
    
    def _execute_task(self, task: GenerationTask):
        """执行任务"""
        try:
            # 调用执行函数
            result = self._execute_func(task)
            
            # 更新任务状态
            with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.output_path = result.get("output_path") if result else None
                task.progress = 100.0
                
                # 移除运行中的任务
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]
            
            # 通知回调
            for callback in self._on_task_complete:
                try:
                    callback(task)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
            
            logger.info(f"任务完成: {task.task_id}")
            
        except Exception as e:
            # 更新任务状态
            with self._lock:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.error_message = str(e)
                
                # 移除运行中的任务
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]
            
            # 通知回调
            for callback in self._on_task_fail:
                try:
                    callback(task)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
            
            logger.error(f"任务失败: {task.task_id}, 错误: {e}")
        
        finally:
            # 尝试执行下一个任务
            with self._lock:
                self._try_execute_next()
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.PENDING:
                # 从等待队列中移除
                if task_id in self._pending_queue:
                    self._pending_queue.remove(task_id)
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                
            elif task.status == TaskStatus.RUNNING:
                # 标记为取消（实际停止需要执行函数支持）
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
            
            # 通知回调
            for callback in self._on_task_cancel:
                try:
                    callback(task)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
            
            logger.info(f"取消任务: {task_id}")
            return True
    
    def get_task(self, task_id: str) -> Optional[GenerationTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[GenerationTask]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_pending_tasks(self) -> List[GenerationTask]:
        """获取等待中的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
    
    def get_running_tasks(self) -> List[GenerationTask]:
        """获取运行中的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]
    
    def get_completed_tasks(self) -> List[GenerationTask]:
        """获取已完成的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.COMPLETED]
    
    def get_failed_tasks(self) -> List[GenerationTask]:
        """获取失败的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.FAILED]
    
    def update_progress(self, task_id: str, progress: float):
        """更新任务进度"""
        task = self._tasks.get(task_id)
        if task:
            task.progress = progress
            
            # 通知回调
            for callback in self._on_progress_update:
                try:
                    callback(task)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
    
    def clear_completed(self):
        """清除已完成的任务"""
        with self._lock:
            completed_ids = [
                task_id for task_id, task in self._tasks.items()
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            ]
            for task_id in completed_ids:
                del self._tasks[task_id]
            logger.info(f"清除 {len(completed_ids)} 个已完成的任务")
    
    def clear_all(self):
        """清除所有任务"""
        with self._lock:
            # 取消所有等待中的任务
            for task_id in list(self._pending_queue):
                task = self._tasks.get(task_id)
                if task:
                    task.status = TaskStatus.CANCELLED
            
            self._pending_queue.clear()
            self._tasks.clear()
            logger.info("清除所有任务")
    
    def on_task_start(self, callback: Callable):
        """注册任务开始回调"""
        self._on_task_start.append(callback)
    
    def on_task_complete(self, callback: Callable):
        """注册任务完成回调"""
        self._on_task_complete.append(callback)
    
    def on_task_fail(self, callback: Callable):
        """注册任务失败回调"""
        self._on_task_fail.append(callback)
    
    def on_task_cancel(self, callback: Callable):
        """注册任务取消回调"""
        self._on_task_cancel.append(callback)
    
    def on_progress_update(self, callback: Callable):
        """注册进度更新回调"""
        self._on_progress_update.append(callback)
    
    def get_queue_status(self) -> Dict[str, int]:
        """获取队列状态"""
        return {
            "total": len(self._tasks),
            "pending": len(self._pending_queue),
            "running": len(self._running_tasks),
            "completed": len(self.get_completed_tasks()),
            "failed": len(self.get_failed_tasks()),
            "cancelled": len([t for t in self._tasks.values() if t.status == TaskStatus.CANCELLED])
        }


# 全局任务队列实例
_task_queue = None


def get_task_queue(max_concurrent: int = 1) -> TaskQueue:
    """获取任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_concurrent)
    return _task_queue
