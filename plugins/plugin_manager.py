"""
插件管理器 - 管理所有插件
"""
import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type

from plugins.base_plugin import (
    BasePlugin, PluginInfo,
    BaseEnginePlugin, BaseLoRAPlugin, 
    BaseControlNetPlugin, BaseEditorPlugin
)
from utils.logger import get_logger

logger = get_logger("plugin")


class PluginManager:
    """插件管理器"""
    
    _instance = None
    
    def __new__(cls, plugins_dir: str = "./plugins"):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, plugins_dir: str = "./plugins"):
        """初始化插件管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._plugins_dir = Path(plugins_dir)
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # 插件存储
        self._plugins: Dict[str, BasePlugin] = {}
        self._engine_plugins: Dict[str, BaseEnginePlugin] = {}
        self._lora_plugins: Dict[str, BaseLoRAPlugin] = {}
        self._controlnet_plugins: Dict[str, BaseControlNetPlugin] = {}
        self._editor_plugins: Dict[str, BaseEditorPlugin] = {}
        
        # 扫描插件
        self._scan_plugins()
    
    def _scan_plugins(self):
        """扫描插件目录"""
        logger.info(f"扫描插件目录: {self._plugins_dir}")
        
        # 添加插件目录到Python路径
        if str(self._plugins_dir) not in sys.path:
            sys.path.insert(0, str(self._plugins_dir))
        
        # 扫描所有Python文件
        for plugin_file in self._plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                self._load_plugin_file(plugin_file)
            except Exception as e:
                logger.error(f"加载插件文件失败 {plugin_file}: {e}")
        
        # 扫描子目录
        for plugin_dir in self._plugins_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                init_file = plugin_dir / "__init__.py"
                if init_file.exists():
                    try:
                        self._load_plugin_module(plugin_dir.name)
                    except Exception as e:
                        logger.error(f"加载插件模块失败 {plugin_dir.name}: {e}")
        
        logger.info(f"已加载 {len(self._plugins)} 个插件")
    
    def _load_plugin_file(self, plugin_file: Path):
        """加载插件文件"""
        module_name = plugin_file.stem
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 查找插件类
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, BasePlugin) and 
                obj is not BasePlugin and
                obj is not BaseEnginePlugin and
                obj is not BaseLoRAPlugin and
                obj is not BaseControlNetPlugin and
                obj is not BaseEditorPlugin):
                
                self._register_plugin_class(obj)
    
    def _load_plugin_module(self, module_name: str):
        """加载插件模块"""
        module = importlib.import_module(module_name)
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, BasePlugin) and 
                obj is not BasePlugin and
                not inspect.isabstract(obj)):
                
                self._register_plugin_class(obj)
    
    def _register_plugin_class(self, plugin_class: Type[BasePlugin]):
        """注册插件类"""
        try:
            # 实例化插件
            plugin = plugin_class()
            info = plugin.info
            
            # 检查是否已存在
            if info.name in self._plugins:
                logger.warning(f"插件已存在: {info.name}")
                return
            
            # 初始化插件
            if plugin.initialize():
                self._plugins[info.name] = plugin
                
                # 根据类型分类
                if isinstance(plugin, BaseEnginePlugin):
                    self._engine_plugins[info.name] = plugin
                elif isinstance(plugin, BaseLoRAPlugin):
                    self._lora_plugins[info.name] = plugin
                elif isinstance(plugin, BaseControlNetPlugin):
                    self._controlnet_plugins[info.name] = plugin
                elif isinstance(plugin, BaseEditorPlugin):
                    self._editor_plugins[info.name] = plugin
                
                logger.info(f"注册插件: {info.name} v{info.version}")
            else:
                logger.warning(f"插件初始化失败: {info.name}")
                
        except Exception as e:
            logger.error(f"注册插件失败: {e}")
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """获取插件"""
        return self._plugins.get(name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """获取所有插件"""
        return self._plugins.copy()
    
    def get_engine_plugins(self) -> Dict[str, BaseEnginePlugin]:
        """获取引擎插件"""
        return self._engine_plugins.copy()
    
    def get_lora_plugins(self) -> Dict[str, BaseLoRAPlugin]:
        """获取LoRA插件"""
        return self._lora_plugins.copy()
    
    def get_controlnet_plugins(self) -> Dict[str, BaseControlNetPlugin]:
        """获取ControlNet插件"""
        return self._controlnet_plugins.copy()
    
    def get_editor_plugins(self) -> Dict[str, BaseEditorPlugin]:
        """获取编辑器插件"""
        return self._editor_plugins.copy()
    
    def enable_plugin(self, name: str) -> bool:
        """启用插件"""
        plugin = self._plugins.get(name)
        if plugin:
            plugin.enable()
            logger.info(f"启用插件: {name}")
            return True
        return False
    
    def disable_plugin(self, name: str) -> bool:
        """禁用插件"""
        plugin = self._plugins.get(name)
        if plugin:
            plugin.disable()
            logger.info(f"禁用插件: {name}")
            return True
        return False
    
    def reload_plugins(self):
        """重新加载所有插件"""
        # 清理现有插件
        for plugin in self._plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"清理插件失败: {e}")
        
        self._plugins.clear()
        self._engine_plugins.clear()
        self._lora_plugins.clear()
        self._controlnet_plugins.clear()
        self._editor_plugins.clear()
        
        # 重新扫描
        self._scan_plugins()
    
    def get_plugins_info(self) -> List[Dict]:
        """获取所有插件信息"""
        return [
            {
                "name": name,
                "enabled": plugin.is_enabled(),
                **plugin.info.to_dict()
            }
            for name, plugin in self._plugins.items()
        ]


# 全局插件管理器实例
_plugin_manager = None


def get_plugin_manager(plugins_dir: str = "./plugins") -> PluginManager:
    """获取插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(plugins_dir)
    return _plugin_manager
