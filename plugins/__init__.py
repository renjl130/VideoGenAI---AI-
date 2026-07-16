"""
VideoGenAI 插件模块
"""
from plugins.base_plugin import (
    BasePlugin, PluginInfo,
    BaseEnginePlugin, BaseLoRAPlugin,
    BaseControlNetPlugin, BaseEditorPlugin
)
from plugins.plugin_manager import PluginManager, get_plugin_manager

__all__ = [
    'BasePlugin',
    'PluginInfo',
    'BaseEnginePlugin',
    'BaseLoRAPlugin',
    'BaseControlNetPlugin',
    'BaseEditorPlugin',
    'PluginManager',
    'get_plugin_manager'
]
