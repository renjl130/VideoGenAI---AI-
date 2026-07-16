"""
GPU监控工具 - 实时监控GPU状态和显存使用
"""
import os
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import pynvml
    pynvml.nvmlInit()
    PYNVML_AVAILABLE = True
except:
    PYNVML_AVAILABLE = False


@dataclass
class GPUInfo:
    """GPU信息数据类"""
    device_id: int
    name: str
    total_memory: int  # MB
    used_memory: int   # MB
    free_memory: int   # MB
    temperature: int   # 摄氏度
    utilization: int   # 百分比
    power_usage: float  # 瓦特
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def memory_usage_percent(self) -> float:
        """显存使用百分比"""
        if self.total_memory == 0:
            return 0.0
        return (self.used_memory / self.total_memory) * 100


class GPUMonitor:
    """GPU监控器"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化GPU监控器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._monitoring = False
        self._monitor_thread = None
        self._callbacks: List[Callable] = []
        self._history: Dict[int, List[GPUInfo]] = {}
        self._update_interval = 1.0  # 秒
        
        # 检测可用的GPU
        self._detect_gpus()
    
    def _detect_gpus(self):
        """检测可用的GPU"""
        self.gpu_count = 0
        self.gpu_names = []
        
        if PYNVML_AVAILABLE:
            try:
                self.gpu_count = pynvml.nvmlDeviceGetCount()
                for i in range(self.gpu_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    self.gpu_names.append(name)
                    self._history[i] = []
            except Exception as e:
                print(f"检测GPU失败: {e}")
        elif TORCH_AVAILABLE and torch.cuda.is_available():
            self.gpu_count = torch.cuda.device_count()
            for i in range(self.gpu_count):
                self.gpu_names.append(torch.cuda.get_device_name(i))
                self._history[i] = []
    
    def get_gpu_info(self, device_id: int = 0) -> Optional[GPUInfo]:
        """获取指定GPU的信息"""
        if device_id >= self.gpu_count:
            return None
        
        if PYNVML_AVAILABLE:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
                
                # 获取显存信息
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_mem = mem_info.total // (1024 * 1024)
                used_mem = mem_info.used // (1024 * 1024)
                free_mem = mem_info.free // (1024 * 1024)
                
                # 获取温度
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temp = 0
                
                # 获取利用率
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_util = util.gpu
                except:
                    gpu_util = 0
                
                # 获取功耗
                try:
                    power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                except:
                    power = 0.0
                
                return GPUInfo(
                    device_id=device_id,
                    name=self.gpu_names[device_id],
                    total_memory=total_mem,
                    used_memory=used_mem,
                    free_memory=free_mem,
                    temperature=temp,
                    utilization=gpu_util,
                    power_usage=power
                )
            except Exception as e:
                print(f"获取GPU信息失败: {e}")
                return None
        
        elif TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                # 使用PyTorch获取信息
                total_mem = torch.cuda.get_device_properties(device_id).total_memory // (1024 * 1024)
                used_mem = torch.cuda.memory_allocated(device_id) // (1024 * 1024)
                free_mem = total_mem - used_mem
                
                return GPUInfo(
                    device_id=device_id,
                    name=self.gpu_names[device_id],
                    total_memory=total_mem,
                    used_memory=used_mem,
                    free_memory=free_mem,
                    temperature=0,
                    utilization=0,
                    power_usage=0.0
                )
            except Exception as e:
                print(f"获取GPU信息失败: {e}")
                return None
        
        return None
    
    def get_all_gpu_info(self) -> List[GPUInfo]:
        """获取所有GPU的信息"""
        infos = []
        for i in range(self.gpu_count):
            info = self.get_gpu_info(i)
            if info:
                infos.append(info)
        return infos
    
    def start_monitoring(self, interval: float = 1.0):
        """开始监控"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._update_interval = interval
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
    
    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            for i in range(self.gpu_count):
                info = self.get_gpu_info(i)
                if info:
                    if i not in self._history:
                        self._history[i] = []
                    self._history[i].append(info)
                    
                    # 保留最近100条记录
                    if len(self._history[i]) > 100:
                        self._history[i] = self._history[i][-100:]
            
            # 调用回调函数
            for callback in self._callbacks:
                try:
                    callback(self.get_all_gpu_info())
                except Exception as e:
                    print(f"回调函数执行失败: {e}")
            
            time.sleep(self._update_interval)
    
    def add_callback(self, callback: Callable):
        """添加监控回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除监控回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_history(self, device_id: int = 0, limit: int = 100) -> List[GPUInfo]:
        """获取历史记录"""
        if device_id in self._history:
            return self._history[device_id][-limit:]
        return []
    
    def clear_cache(self):
        """清除GPU缓存"""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def get_optimal_batch_size(self, device_id: int = 0, model_size_mb: int = 1000) -> int:
        """根据显存估算最优批次大小"""
        info = self.get_gpu_info(device_id)
        if not info:
            return 1
        
        # 预留20%显存作为缓冲
        available = info.free_memory * 0.8
        if available < model_size_mb:
            return 1
        
        return max(1, int(available / model_size_mb))


# 全局GPU监控实例
gpu_monitor = GPUMonitor()


def get_gpu_monitor() -> GPUMonitor:
    """获取GPU监控实例"""
    return gpu_monitor


def format_memory(mb: int) -> str:
    """格式化显存显示"""
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb} MB"


def format_gpu_info(info: GPUInfo) -> str:
    """格式化GPU信息显示"""
    return (
        f"GPU {info.device_id}: {info.name}\n"
        f"  显存: {format_memory(info.used_memory)}/{format_memory(info.total_memory)} "
        f"({info.memory_usage_percent:.1f}%)\n"
        f"  温度: {info.temperature}°C\n"
        f"  利用率: {info.utilization}%\n"
        f"  功耗: {info.power_usage:.1f}W"
    )
