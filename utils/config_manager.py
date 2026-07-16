"""
配置管理器 - 负责加载、保存和管理所有配置
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AppConfig:
    """应用配置数据类"""
    name: str = "VideoGenAI"
    version: str = "1.0.0"
    language: str = "zh_CN"
    theme: str = "dark"


@dataclass
class ModelConfig:
    """模型配置数据类"""
    default_model: str = "wan2.1-t2v-1.3b"
    models_dir: str = "./models"
    loras_dir: str = "./loras"
    cache_dir: str = "./cache"
    auto_download: bool = True
    mirror: str = "huggingface"


@dataclass
class GenerationConfig:
    """生成配置数据类"""
    default_resolution: str = "832x480"
    default_fps: int = 16
    default_frames: int = 81
    default_steps: int = 50
    default_cfg_scale: float = 5.0
    default_seed: int = -1
    negative_prompt: str = ""


@dataclass
class OptimizationConfig:
    """优化配置数据类"""
    precision: str = "auto"
    torch_compile: bool = False
    flash_attention: bool = True
    xformers: bool = True
    sage_attention: bool = False
    cpu_offload: bool = False
    sequential_offload: bool = False
    attention_slicing: bool = False
    vae_tiling: bool = True
    low_vram_mode: bool = False
    high_performance_mode: bool = False


@dataclass
class OutputConfig:
    """输出配置数据类"""
    output_dir: str = "./outputs"
    auto_save_history: bool = True
    auto_save_prompt: bool = True
    filename_pattern: str = "{timestamp}_{model}_{seed}"


@dataclass
class GPUConfig:
    """GPU配置数据类"""
    device_id: int = 0
    memory_fraction: float = 0.9
    auto_manage_memory: bool = True


@dataclass
class QueueConfig:
    """队列配置数据类"""
    max_concurrent: int = 1
    auto_retry: bool = True
    max_retries: int = 3


class ConfigManager:
    """配置管理器主类"""
    
    _instance = None
    _config: Dict[str, Any] = {}
    _config_path: str = ""
    
    def __new__(cls, config_path: Optional[str] = None):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._config_path = config_path or self._get_default_config_path()
        self._config = {}
        self.load()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        base_dir = Path(__file__).parent.parent
        return str(base_dir / "configs" / "config.json")
    
    def load(self) -> Dict[str, Any]:
        """加载配置文件"""
        # 先加载默认配置
        default_config_path = Path(__file__).parent.parent / "configs" / "default_config.json"
        if default_config_path.exists():
            with open(default_config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        
        # 加载用户配置（如果存在）
        if os.path.exists(self._config_path):
            with open(self._config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                self._merge_config(self._config, user_config)
        else:
            # 保存默认配置
            self.save()
        
        return self._config
    
    def save(self):
        """保存配置到文件"""
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)
    
    def _merge_config(self, base: Dict, override: Dict):
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值，支持点号分隔的路径"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取整个配置段"""
        return self._config.get(section, {})
    
    def update_section(self, section: str, data: Dict[str, Any]):
        """更新整个配置段"""
        if section in self._config:
            self._config[section].update(data)
        else:
            self._config[section] = data
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def reset(self):
        """重置为默认配置"""
        default_config_path = Path(__file__).parent.parent / "configs" / "default_config.json"
        if default_config_path.exists():
            with open(default_config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            self.save()
    
    @property
    def app(self) -> AppConfig:
        """获取应用配置"""
        data = self.get_section('app')
        return AppConfig(**data)
    
    @property
    def models(self) -> ModelConfig:
        """获取模型配置"""
        data = self.get_section('models')
        return ModelConfig(**data)
    
    @property
    def generation(self) -> GenerationConfig:
        """获取生成配置"""
        data = self.get_section('generation')
        return GenerationConfig(**data)
    
    @property
    def optimization(self) -> OptimizationConfig:
        """获取优化配置"""
        data = self.get_section('optimization')
        return OptimizationConfig(**data)
    
    @property
    def output(self) -> OutputConfig:
        """获取输出配置"""
        data = self.get_section('output')
        return OutputConfig(**data)
    
    @property
    def gpu(self) -> GPUConfig:
        """获取GPU配置"""
        data = self.get_section('gpu')
        return GPUConfig(**data)
    
    @property
    def queue(self) -> QueueConfig:
        """获取队列配置"""
        data = self.get_section('queue')
        return QueueConfig(**data)


# 全局配置实例
_config_manager = None


def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def reload_config(config_path: Optional[str] = None):
    """重新加载配置"""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager
