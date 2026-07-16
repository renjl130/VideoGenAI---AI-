"""
插件基类 - 定义插件接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginInfo:
    """插件信息"""

    name: str
    version: str
    author: str
    description: str
    plugin_type: str  # engine, lora, controlnet, editor
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "plugin_type": self.plugin_type,
            "dependencies": list(self.dependencies),
        }


class BasePlugin(ABC):
    """插件基类"""

    def __init__(self):
        """初始化插件"""
        self._enabled = False

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """插件信息"""
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """初始化插件"""
        pass

    @abstractmethod
    def cleanup(self):
        """清理插件"""
        pass

    def enable(self):
        """启用插件"""
        self._enabled = False

    def disable(self):
        """禁用插件"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """检查插件是否启用"""
        return self._enabled


class BaseEnginePlugin(BasePlugin):
    """引擎插件基类"""

    @abstractmethod
    def get_engine_class(self):
        """获取引擎类"""
        pass

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """获取支持的模型列表"""
        pass


class BaseLoRAPlugin(BasePlugin):
    """LoRA插件基类"""

    @abstractmethod
    def get_lora_info(self, lora_path: str) -> dict[str, Any]:
        """获取LoRA信息"""
        pass

    @abstractmethod
    def apply_lora(self, model, lora_path: str, strength: float = 1.0):
        """应用LoRA"""
        pass


class BaseControlNetPlugin(BasePlugin):
    """ControlNet插件基类"""

    @abstractmethod
    def get_control_types(self) -> list[str]:
        """获取支持的控制类型"""
        pass

    @abstractmethod
    def preprocess(self, image, control_type: str) -> Any:
        """预处理控制图像"""
        pass

    @abstractmethod
    def apply_control(self, model, control_image, control_type: str, strength: float):
        """应用控制"""
        pass


class BaseEditorPlugin(BasePlugin):
    """视频编辑插件基类"""

    @abstractmethod
    def get_edit_operations(self) -> list[str]:
        """获取支持的编辑操作"""
        pass

    @abstractmethod
    def edit_video(self, video_path: str, operation: str, **kwargs) -> str:
        """编辑视频"""
        pass
