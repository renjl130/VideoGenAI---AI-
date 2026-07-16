"""
VideoGenAI 插件模块
"""

from plugins.base_plugin import (
    BaseControlNetPlugin,
    BaseEditorPlugin,
    BaseEnginePlugin,
    BaseLoRAPlugin,
    BasePlugin,
    PluginInfo,
)
from plugins.plugin_manager import PluginManager, get_plugin_manager
from plugins.plugin_manifest import (
    PLUGIN_API_VERSION,
    PluginManifest,
    PluginManifestError,
)

__all__ = [
    "BasePlugin",
    "PluginInfo",
    "BaseEnginePlugin",
    "BaseLoRAPlugin",
    "BaseControlNetPlugin",
    "BaseEditorPlugin",
    "PluginManager",
    "get_plugin_manager",
    "PLUGIN_API_VERSION",
    "PluginManifestError",
    "PluginManifest",
]
