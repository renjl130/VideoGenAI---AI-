"""
历史记录管理器 - 管理生成历史和Prompt历史
"""

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from utils.logger import get_logger
from utils.paths import APP_PATHS, resolve_project_path

logger = get_logger("history")


@dataclass
class HistoryRecord:
    """历史记录"""

    record_id: str
    task_type: str
    model_id: str
    prompt: str
    negative_prompt: str
    parameters: dict[str, Any]
    output_path: str
    created_at: str
    duration: float  # 生成耗时（秒）
    file_size: int  # 文件大小（字节）
    tags: list[str] = field(default_factory=list)
    status: str = "completed"
    error_kind: str | None = None
    error_message: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class HistoryManager:
    """历史记录管理器"""

    _instance: ClassVar["HistoryManager | None"] = None
    _initialized: bool

    def __new__(cls, history_dir: str | None = None):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, history_dir: str | None = None):
        """初始化历史记录管理器"""
        if self._initialized:
            return

        self._initialized = True
        self._history_dir = resolve_project_path(history_dir) if history_dir else APP_PATHS.history
        self._history_dir.mkdir(parents=True, exist_ok=True)

        self._history_file = self._history_dir / "history.json"
        self._prompt_file = self._history_dir / "prompts.json"

        # 加载历史记录
        self._history: list[HistoryRecord] = []
        self._prompts: list[dict[str, Any]] = []
        self._lock = threading.RLock()

        self._load_history()
        self._load_prompts()

    def _load_history(self):
        """加载历史记录"""
        if self._history_file.exists():
            try:
                with open(self._history_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self._history = [HistoryRecord(**record) for record in data]
                logger.info(f"加载 {len(self._history)} 条历史记录")
            except Exception as e:
                logger.error(f"加载历史记录失败: {e}")
                self._history = []

    @staticmethod
    def _atomic_write_json(path: Path, data: Any):
        """通过同目录临时文件原子替换 JSON。"""
        temp_path = path.with_name(f"{path.name}.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def _save_history(self):
        """原子保存历史记录。"""
        try:
            self._atomic_write_json(
                self._history_file,
                [record.to_dict() for record in self._history],
            )
        except Exception:
            logger.exception("保存历史记录失败")

    def _load_prompts(self):
        """加载Prompt历史"""
        if self._prompt_file.exists():
            try:
                with open(self._prompt_file, encoding="utf-8") as f:
                    self._prompts = json.load(f)
                logger.info(f"加载 {len(self._prompts)} 条Prompt记录")
            except Exception as e:
                logger.error(f"加载Prompt记录失败: {e}")
                self._prompts = []

    def _save_prompts(self):
        """原子保存 Prompt 历史。"""
        try:
            self._atomic_write_json(self._prompt_file, self._prompts)
        except Exception:
            logger.exception("保存Prompt记录失败")

    def add_record(self, record: HistoryRecord):
        """添加生成历史；Prompt 使用次数在任务提交时单独记录。"""
        with self._lock:
            self._history.append(record)
            self._save_history()
        logger.info(f"添加历史记录: {record.record_id}")

    def add_prompt(self, prompt: str, model_id: str = "", task_type: str = ""):
        """线程安全地添加或更新 Prompt 记录。"""
        if not prompt.strip():
            return
        now = datetime.now().isoformat()
        with self._lock:
            for item in self._prompts:
                if item.get("prompt") == prompt:
                    item["use_count"] = item.get("use_count", 0) + 1
                    item["last_used"] = now
                    self._save_prompts()
                    return

            self._prompts.append(
                {
                    "prompt": prompt,
                    "model_id": model_id,
                    "task_type": task_type,
                    "use_count": 1,
                    "created_at": now,
                    "last_used": now,
                }
            )
            if len(self._prompts) > 1000:
                self._prompts = self._prompts[-1000:]
            self._save_prompts()

    def get_history(
        self,
        limit: int = 100,
        offset: int = 0,
        model_id: str | None = None,
        task_type: str | None = None,
    ) -> list[HistoryRecord]:
        """获取历史记录"""
        with self._lock:
            filtered = list(self._history)

        if model_id:
            filtered = [r for r in filtered if r.model_id == model_id]

        if task_type:
            filtered = [r for r in filtered if r.task_type == task_type]

        # 按时间倒序，不修改内部存储顺序
        filtered.sort(key=lambda x: x.created_at, reverse=True)

        return filtered[offset : offset + limit]

    def get_record(self, record_id: str) -> HistoryRecord | None:
        """获取单条记录"""
        for record in self._history:
            if record.record_id == record_id:
                return record
        return None

    def delete_record(self, record_id: str) -> bool:
        """删除记录"""
        for i, record in enumerate(self._history):
            if record.record_id == record_id:
                del self._history[i]
                self._save_history()
                logger.info(f"删除历史记录: {record_id}")
                return True
        return False

    def clear_history(self):
        """清空历史记录"""
        self._history.clear()
        self._save_history()
        logger.info("清空历史记录")

    def get_prompts(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取Prompt历史"""
        # 按使用次数排序
        with self._lock:
            prompts = [dict(item) for item in self._prompts]
        sorted_prompts = sorted(prompts, key=lambda x: x.get("use_count", 0), reverse=True)
        return sorted_prompts[:limit]

    def search_prompts(self, keyword: str) -> list[dict[str, Any]]:
        """搜索Prompt"""
        keyword = keyword.lower()
        with self._lock:
            return [
                dict(item) for item in self._prompts if keyword in item.get("prompt", "").lower()
            ]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        if not self._history:
            return {
                "total_records": 0,
                "total_duration": 0,
                "total_size": 0,
                "models_used": {},
                "task_types": {},
            }

        total_duration = sum(r.duration for r in self._history)
        total_size = sum(r.file_size for r in self._history)

        models_used: dict[str, int] = {}
        for record in self._history:
            models_used[record.model_id] = models_used.get(record.model_id, 0) + 1

        task_types: dict[str, int] = {}
        for record in self._history:
            task_types[record.task_type] = task_types.get(record.task_type, 0) + 1

        return {
            "total_records": len(self._history),
            "total_duration": total_duration,
            "total_size": total_size,
            "models_used": models_used,
            "task_types": task_types,
        }

    def export_history(self, export_path: str):
        """导出历史记录"""
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "history": [record.to_dict() for record in self._history],
                        "prompts": self._prompts,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info(f"导出历史记录到: {export_path}")
        except Exception as e:
            logger.error(f"导出历史记录失败: {e}")

    def import_history(self, import_path: str):
        """导入历史记录"""
        try:
            with open(import_path, encoding="utf-8") as f:
                data = json.load(f)

            if "history" in data:
                new_records = [HistoryRecord(**record) for record in data["history"]]
                self._history.extend(new_records)
                self._save_history()

            if "prompts" in data:
                self._prompts.extend(data["prompts"])
                self._save_prompts()

            logger.info("导入历史记录成功")
        except Exception as e:
            logger.error(f"导入历史记录失败: {e}")


# 全局历史记录管理器实例
_history_manager = None


def get_history_manager(history_dir: str | None = None) -> HistoryManager:
    """获取历史记录管理器实例"""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager(history_dir)
    return _history_manager
