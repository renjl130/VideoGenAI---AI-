"""
任务队列管理器 - 管理视频生成任务和协作式取消。
"""

import threading
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from utils.inference_errors import InferenceRuntimeError
from utils.logger import get_logger

logger = get_logger("task_queue")


class TaskStatus(Enum):
    """任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(Enum):
    """任务类型枚举。"""

    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_CONTINUATION = "video_continuation"
    VIDEO_EXTENSION = "video_extension"


@dataclass
class GenerationTask:
    """视频生成任务。"""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: TaskType = TaskType.TEXT_TO_VIDEO
    status: TaskStatus = TaskStatus.PENDING

    model_id: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    image_path: str | None = None
    video_path: str | None = None

    width: int = 832
    height: int = 480
    num_frames: int = 81
    fps: int = 16
    steps: int = 50
    cfg_scale: float = 5.0
    seed: int = -1

    precision: str = "auto"
    cpu_offload: bool = False
    vae_tiling: bool = True
    output_filename_pattern: str = "{timestamp}_{model}_{seed}"

    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    output_path: str | None = None
    error_message: str | None = None
    error_kind: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    prompt_history: list[str] = field(default_factory=list)

    cancel_event: threading.Event = field(
        default_factory=threading.Event,
        repr=False,
        compare=False,
    )
    _cancel_notified: bool = field(
        default=False,
        init=False,
        repr=False,
        compare=False,
    )

    def request_cancel(self):
        """请求协作式取消。"""
        self.cancel_event.set()

    def is_cancel_requested(self) -> bool:
        """返回任务是否已收到取消请求。"""
        return self.cancel_event.is_set()

    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化字典。"""
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
            "output_filename_pattern": self.output_filename_pattern,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "output_path": self.output_path,
            "error_message": self.error_message,
            "error_kind": self.error_kind,
            "error_details": self.error_details,
            "progress": self.progress,
        }


class TaskQueue:
    """线程安全的内存任务队列。"""

    _instance: ClassVar["TaskQueue | None"] = None
    _initialized: bool

    def __new__(cls, max_concurrent: int = 1):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_concurrent: int = 1):
        if self._initialized:
            return

        self._initialized = True
        self._max_concurrent = max(1, int(max_concurrent))
        self._tasks: dict[str, GenerationTask] = {}
        self._pending_queue: deque[str] = deque()
        self._running_tasks: dict[str, threading.Thread] = {}

        self._on_task_start: list[Callable] = []
        self._on_task_complete: list[Callable] = []
        self._on_task_fail: list[Callable] = []
        self._on_task_cancel: list[Callable] = []
        self._on_progress_update: list[Callable] = []

        self._execute_func: Callable | None = None
        self._lock = threading.RLock()
        logger.info(
            "任务队列初始化，最大并发数: %s",
            self._max_concurrent,
        )

    @staticmethod
    def _notify(callbacks: list[Callable], task: GenerationTask, event: str):
        """调用回调快照，避免回调修改注册列表影响当前遍历。"""
        for callback in callbacks:
            try:
                callback(task)
            except Exception:
                logger.exception("%s 回调执行失败", event)

    def set_execute_function(self, func: Callable):
        with self._lock:
            self._execute_func = func

    def add_task(self, task: GenerationTask) -> str:
        with self._lock:
            if task.task_id in self._tasks:
                raise ValueError(f"任务 ID 已存在: {task.task_id}")
            task.status = TaskStatus.PENDING
            self._tasks[task.task_id] = task
            self._pending_queue.append(task.task_id)

        logger.info("添加任务: %s, 类型: %s", task.task_id, task.task_type.value)
        self._try_execute_next()
        return task.task_id

    def _try_execute_next(self):
        to_start = []
        with self._lock:
            if self._execute_func is None:
                if self._pending_queue:
                    logger.warning("未设置执行函数")
                return

            while len(self._running_tasks) < self._max_concurrent and self._pending_queue:
                task_id = self._pending_queue.popleft()
                task = self._tasks.get(task_id)
                if task is None or task.is_cancel_requested():
                    continue

                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                thread = threading.Thread(
                    target=self._execute_task,
                    args=(task,),
                    daemon=True,
                    name=f"generation-{task.task_id}",
                )
                self._running_tasks[task_id] = thread
                callbacks = list(self._on_task_start)
                to_start.append((task, thread, callbacks))

        for task, thread, callbacks in to_start:
            self._notify(callbacks, task, "任务开始")
            logger.info("开始执行任务: %s", task.task_id)
            thread.start()

    def _finish_cancelled_locked(
        self,
        task: GenerationTask,
        release_slot: bool = True,
    ) -> list[Callable]:
        task.status = TaskStatus.CANCELLED
        task.completed_at = task.completed_at or datetime.now()
        if release_slot:
            self._running_tasks.pop(task.task_id, None)
        if task._cancel_notified:
            return []
        task._cancel_notified = True
        return list(self._on_task_cancel)

    def _execute_task(self, task: GenerationTask):
        callbacks: list[Callable] = []
        event = ""
        try:
            if task.is_cancel_requested():
                with self._lock:
                    callbacks = self._finish_cancelled_locked(task)
                event = "任务取消"
            else:
                execute_func = self._execute_func
                if execute_func is None:
                    raise RuntimeError("未设置任务执行函数")
                result = execute_func(task)

                with self._lock:
                    if task.is_cancel_requested() or task.status is TaskStatus.CANCELLED:
                        callbacks = self._finish_cancelled_locked(task)
                        event = "任务取消"
                    else:
                        task.status = TaskStatus.COMPLETED
                        task.completed_at = datetime.now()
                        task.output_path = result.get("output_path") if result else None
                        task.progress = 100.0
                        self._running_tasks.pop(task.task_id, None)
                        callbacks = list(self._on_task_complete)
                        event = "任务完成"
        except Exception as error:
            with self._lock:
                if task.is_cancel_requested() or task.status is TaskStatus.CANCELLED:
                    callbacks = self._finish_cancelled_locked(task)
                    event = "任务取消"
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    task.error_message = str(error)
                    if isinstance(error, InferenceRuntimeError):
                        task.error_kind = error.report.kind.value
                        task.error_details = error.report.to_dict()
                    self._running_tasks.pop(task.task_id, None)
                    callbacks = list(self._on_task_fail)
                    event = "任务失败"
            if event == "任务失败":
                logger.exception("任务失败: %s", task.task_id)
        finally:
            if callbacks:
                self._notify(callbacks, task, event)
            logger.info("%s: %s", event or "任务结束", task.task_id)
            self._try_execute_next()

    def cancel_task(self, task_id: str) -> bool:
        callbacks: list[Callable] = []
        task: GenerationTask | None
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                return False

            was_running = task.status is TaskStatus.RUNNING
            task.request_cancel()
            if task.status is TaskStatus.PENDING:
                try:
                    self._pending_queue.remove(task_id)
                except ValueError:
                    pass
            callbacks = self._finish_cancelled_locked(
                task,
                release_slot=not was_running,
            )

        if callbacks:
            self._notify(callbacks, task, "任务取消")
        logger.info("取消任务: %s", task_id)
        self._try_execute_next()
        return True

    def get_task(self, task_id: str) -> GenerationTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[GenerationTask]:
        with self._lock:
            return list(self._tasks.values())

    def _get_tasks_by_status(self, status: TaskStatus) -> list[GenerationTask]:
        with self._lock:
            return [task for task in self._tasks.values() if task.status is status]

    def get_pending_tasks(self) -> list[GenerationTask]:
        return self._get_tasks_by_status(TaskStatus.PENDING)

    def get_running_tasks(self) -> list[GenerationTask]:
        return self._get_tasks_by_status(TaskStatus.RUNNING)

    def get_completed_tasks(self) -> list[GenerationTask]:
        return self._get_tasks_by_status(TaskStatus.COMPLETED)

    def get_failed_tasks(self) -> list[GenerationTask]:
        return self._get_tasks_by_status(TaskStatus.FAILED)

    def update_progress(self, task_id: str, progress: float):
        callbacks: list[Callable] = []
        task: GenerationTask | None
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status is not TaskStatus.RUNNING:
                return
            task.progress = max(0.0, min(float(progress), 100.0))
            callbacks = list(self._on_progress_update)
        self._notify(callbacks, task, "进度更新")

    def clear_completed(self):
        with self._lock:
            completed_ids = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status
                in {
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                }
                and task_id not in self._running_tasks
            ]
            for task_id in completed_ids:
                del self._tasks[task_id]
        logger.info("清除 %s 个终态任务", len(completed_ids))

    def clear_all(self):
        with self._lock:
            task_ids = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}
            ]
        for task_id in task_ids:
            self.cancel_task(task_id)
        self.clear_completed()

    def _add_callback(self, callbacks: list[Callable], callback: Callable):
        with self._lock:
            if callback not in callbacks:
                callbacks.append(callback)

    def on_task_start(self, callback: Callable):
        self._add_callback(self._on_task_start, callback)

    def on_task_complete(self, callback: Callable):
        self._add_callback(self._on_task_complete, callback)

    def on_task_fail(self, callback: Callable):
        self._add_callback(self._on_task_fail, callback)

    def on_task_cancel(self, callback: Callable):
        self._add_callback(self._on_task_cancel, callback)

    def on_progress_update(self, callback: Callable):
        self._add_callback(self._on_progress_update, callback)

    def get_queue_status(self) -> dict[str, int]:
        with self._lock:
            statuses = [task.status for task in self._tasks.values()]
            return {
                "total": len(statuses),
                "pending": len(self._pending_queue),
                "running": len(self._running_tasks),
                "completed": statuses.count(TaskStatus.COMPLETED),
                "failed": statuses.count(TaskStatus.FAILED),
                "cancelled": statuses.count(TaskStatus.CANCELLED),
            }


_task_queue = None


def get_task_queue(max_concurrent: int = 1) -> TaskQueue:
    """获取任务队列实例。"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(max_concurrent)
    return _task_queue
