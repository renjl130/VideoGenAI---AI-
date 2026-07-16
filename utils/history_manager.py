"""
历史记录管理器 - 管理生成历史和Prompt历史
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("history")


@dataclass
class HistoryRecord:
    """历史记录"""
    record_id: str
    task_type: str
    model_id: str
    prompt: str
    negative_prompt: str
    parameters: Dict[str, Any]
    output_path: str
    created_at: str
    duration: float  # 生成耗时（秒）
    file_size: int  # 文件大小（字节）
    tags: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class HistoryManager:
    """历史记录管理器"""
    
    _instance = None
    
    def __new__(cls, history_dir: str = "./outputs/history"):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, history_dir: str = "./outputs/history"):
        """初始化历史记录管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._history_dir = Path(history_dir)
        self._history_dir.mkdir(parents=True, exist_ok=True)
        
        self._history_file = self._history_dir / "history.json"
        self._prompt_file = self._history_dir / "prompts.json"
        
        # 加载历史记录
        self._history: List[HistoryRecord] = []
        self._prompts: List[Dict[str, Any]] = []
        
        self._load_history()
        self._load_prompts()
    
    def _load_history(self):
        """加载历史记录"""
        if self._history_file.exists():
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = [HistoryRecord(**record) for record in data]
                logger.info(f"加载 {len(self._history)} 条历史记录")
            except Exception as e:
                logger.error(f"加载历史记录失败: {e}")
                self._history = []
    
    def _save_history(self):
        """保存历史记录"""
        try:
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump([record.to_dict() for record in self._history], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
    
    def _load_prompts(self):
        """加载Prompt历史"""
        if self._prompt_file.exists():
            try:
                with open(self._prompt_file, 'r', encoding='utf-8') as f:
                    self._prompts = json.load(f)
                logger.info(f"加载 {len(self._prompts)} 条Prompt记录")
            except Exception as e:
                logger.error(f"加载Prompt记录失败: {e}")
                self._prompts = []
    
    def _save_prompts(self):
        """保存Prompt历史"""
        try:
            with open(self._prompt_file, 'w', encoding='utf-8') as f:
                json.dump(self._prompts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存Prompt记录失败: {e}")
    
    def add_record(self, record: HistoryRecord):
        """添加历史记录"""
        self._history.append(record)
        self._save_history()
        
        # 同时保存Prompt
        self.add_prompt(record.prompt, record.model_id, record.task_type)
        
        logger.info(f"添加历史记录: {record.record_id}")
    
    def add_prompt(self, prompt: str, model_id: str = "", task_type: str = ""):
        """添加Prompt记录"""
        # 检查是否已存在
        for p in self._prompts:
            if p["prompt"] == prompt:
                # 更新使用次数
                p["use_count"] = p.get("use_count", 0) + 1
                p["last_used"] = datetime.now().isoformat()
                self._save_prompts()
                return
        
        # 添加新记录
        self._prompts.append({
            "prompt": prompt,
            "model_id": model_id,
            "task_type": task_type,
            "use_count": 1,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        })
        
        # 限制保存的Prompt数量
        if len(self._prompts) > 1000:
            self._prompts = self._prompts[-1000:]
        
        self._save_prompts()
    
    def get_history(self, 
                    limit: int = 100, 
                    offset: int = 0,
                    model_id: Optional[str] = None,
                    task_type: Optional[str] = None) -> List[HistoryRecord]:
        """获取历史记录"""
        filtered = self._history
        
        if model_id:
            filtered = [r for r in filtered if r.model_id == model_id]
        
        if task_type:
            filtered = [r for r in filtered if r.task_type == task_type]
        
        # 按时间倒序
        filtered.sort(key=lambda x: x.created_at, reverse=True)
        
        return filtered[offset:offset + limit]
    
    def get_record(self, record_id: str) -> Optional[HistoryRecord]:
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
    
    def get_prompts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取Prompt历史"""
        # 按使用次数排序
        sorted_prompts = sorted(self._prompts, key=lambda x: x.get("use_count", 0), reverse=True)
        return sorted_prompts[:limit]
    
    def search_prompts(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索Prompt"""
        keyword = keyword.lower()
        return [p for p in self._prompts if keyword in p["prompt"].lower()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._history:
            return {
                "total_records": 0,
                "total_duration": 0,
                "total_size": 0,
                "models_used": {},
                "task_types": {}
            }
        
        total_duration = sum(r.duration for r in self._history)
        total_size = sum(r.file_size for r in self._history)
        
        models_used = {}
        for record in self._history:
            models_used[record.model_id] = models_used.get(record.model_id, 0) + 1
        
        task_types = {}
        for record in self._history:
            task_types[record.task_type] = task_types.get(record.task_type, 0) + 1
        
        return {
            "total_records": len(self._history),
            "total_duration": total_duration,
            "total_size": total_size,
            "models_used": models_used,
            "task_types": task_types
        }
    
    def export_history(self, export_path: str):
        """导出历史记录"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "history": [record.to_dict() for record in self._history],
                    "prompts": self._prompts
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"导出历史记录到: {export_path}")
        except Exception as e:
            logger.error(f"导出历史记录失败: {e}")
    
    def import_history(self, import_path: str):
        """导入历史记录"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "history" in data:
                new_records = [HistoryRecord(**record) for record in data["history"]]
                self._history.extend(new_records)
                self._save_history()
            
            if "prompts" in data:
                self._prompts.extend(data["prompts"])
                self._save_prompts()
            
            logger.info(f"导入历史记录成功")
        except Exception as e:
            logger.error(f"导入历史记录失败: {e}")


# 全局历史记录管理器实例
_history_manager = None


def get_history_manager(history_dir: str = "./outputs/history") -> HistoryManager:
    """获取历史记录管理器实例"""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager(history_dir)
    return _history_manager
