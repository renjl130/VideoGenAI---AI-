"""
示例插件 - 展示如何创建插件
"""
from typing import Dict, List, Any
from plugins.base_plugin import BasePlugin, PluginInfo


class ExamplePlugin(BasePlugin):
    """示例插件"""
    
    @property
    def info(self) -> PluginInfo:
        """插件信息"""
        return PluginInfo(
            name="example",
            version="1.0.0",
            author="VideoGenAI",
            description="示例插件，展示插件开发方法",
            plugin_type="utility",
            dependencies=[]
        )
    
    def initialize(self) -> bool:
        """初始化插件"""
        print(f"初始化插件: {self.info.name}")
        return True
    
    def cleanup(self):
        """清理插件"""
        print(f"清理插件: {self.info.name}")
    
    def hello(self) -> str:
        """示例方法"""
        return "Hello from Example Plugin!"
