"""
日志管理器 - 提供统一的日志记录功能
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging
from logging.handlers import RotatingFileHandler


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class LogManager:
    """日志管理器"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化日志管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._log_dir = Path(__file__).parent.parent / "logs"
        self._log_dir.mkdir(exist_ok=True)
        
        # 配置根日志记录器
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """配置根日志记录器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 文件处理器
        log_file = self._log_dir / f"videogenai_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        return self._loggers[name]
    
    def set_level(self, level: str):
        """设置日志级别"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        if level.upper() in level_map:
            logging.getLogger().setLevel(level_map[level.upper()])
    
    def get_log_files(self):
        """获取所有日志文件"""
        return list(self._log_dir.glob("*.log"))
    
    def clear_old_logs(self, days: int = 7):
        """清理旧日志文件"""
        cutoff = datetime.now().timestamp() - (days * 86400)
        for log_file in self._log_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()


def get_logger(name: str) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return LogManager().get_logger(name)


# 预定义的日志记录器
app_logger = get_logger("app")
model_logger = get_logger("model")
engine_logger = get_logger("engine")
queue_logger = get_logger("queue")
ui_logger = get_logger("ui")
