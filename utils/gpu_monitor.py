"""
GPU监控工具 - 实时监控GPU状态和显存使用
"""
import os
import time
import subprocess
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("gpu_monitor")


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
    driver_version: str = ""
    cuda_version: str = ""
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
        self._update_interval = 1.0
        
        # GPU检测状态
        self.gpu_count = 0
        self.gpu_names = []
        self._detection_method = None
        
        # 检测GPU
        self._detect_gpus()
    
    def _detect_gpus(self):
        """检测可用的GPU - 多种方法"""
        logger.info("开始检测GPU...")
        
        # 方法1: 尝试使用nvidia-smi
        if self._detect_via_nvidia_smi():
            self._detection_method = "nvidia-smi"
            logger.info(f"通过nvidia-smi检测到 {self.gpu_count} 个GPU")
            return
        
        # 方法2: 尝试使用torch
        if self._detect_via_torch():
            self._detection_method = "torch"
            logger.info(f"通过PyTorch检测到 {self.gpu_count} 个GPU")
            return
        
        # 方法3: 尝试使用nvidia-ml-py/pynvml
        if self._detect_via_nvml():
            self._detection_method = "nvml"
            logger.info(f"通过NVML检测到 {self.gpu_count} 个GPU")
            return
        
        # 未检测到GPU
        self._detection_method = "none"
        logger.warning("未检测到NVIDIA GPU")
    
    def _detect_via_nvidia_smi(self) -> bool:
        """通过nvidia-smi检测GPU"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,power.draw,driver_version", 
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return False
            
            lines = result.stdout.strip().split('\n')
            if not lines or not lines[0]:
                return False
            
            self.gpu_count = len(lines)
            self.gpu_names = []
            
            for i, line in enumerate(lines):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 8:
                    self.gpu_names.append(parts[0])
                    
                    # 保存初始信息
                    if i not in self._history:
                        self._history[i] = []
                    
                    info = GPUInfo(
                        device_id=i,
                        name=parts[0],
                        total_memory=int(float(parts[1])),
                        used_memory=int(float(parts[2])),
                        free_memory=int(float(parts[3])),
                        temperature=int(float(parts[4])),
                        utilization=int(float(parts[5])),
                        power_usage=float(parts[6]),
                        driver_version=parts[7]
                    )
                    self._history[i].append(info)
            
            return True
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"nvidia-smi检测失败: {e}")
            return False
    
    def _detect_via_torch(self) -> bool:
        """通过PyTorch检测GPU"""
        try:
            import torch
            
            if not torch.cuda.is_available():
                return False
            
            self.gpu_count = torch.cuda.device_count()
            self.gpu_names = []
            
            for i in range(self.gpu_count):
                name = torch.cuda.get_device_name(i)
                self.gpu_names.append(name)
                
                # 获取显存信息
                props = torch.cuda.get_device_properties(i)
                total_mem = props.total_memory // (1024 * 1024)
                
                if i not in self._history:
                    self._history[i] = []
                
                info = GPUInfo(
                    device_id=i,
                    name=name,
                    total_memory=total_mem,
                    used_memory=0,
                    free_memory=total_mem,
                    temperature=0,
                    utilization=0,
                    power_usage=0.0,
                    cuda_version=torch.version.cuda or ""
                )
                self._history[i].append(info)
            
            return True
            
        except Exception as e:
            logger.debug(f"PyTorch检测失败: {e}")
            return False
    
    def _detect_via_nvml(self) -> bool:
        """通过NVML检测GPU"""
        try:
            # 尝试nvidia-ml-py
            try:
                import nvidia_ml_py as nvml
                nvml.nvmlInit()
            except ImportError:
                import pynvml
                nvml = pynvml
                nvml.nvmlInit()
            
            self.gpu_count = nvml.nvmlDeviceGetCount()
            self.gpu_names = []
            
            for i in range(self.gpu_count):
                handle = nvml.nvmlDeviceGetHandleByIndex(i)
                name = nvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                self.gpu_names.append(name)
                
                if i not in self._history:
                    self._history[i] = []
            
            return True
            
        except Exception as e:
            logger.debug(f"NVML检测失败: {e}")
            return False
    
    def get_gpu_info(self, device_id: int = 0) -> Optional[GPUInfo]:
        """获取指定GPU的信息"""
        if device_id >= self.gpu_count:
            return None
        
        # 根据检测方法获取信息
        if self._detection_method == "nvidia-smi":
            return self._get_info_nvidia_smi(device_id)
        elif self._detection_method == "torch":
            return self._get_info_torch(device_id)
        elif self._detection_method == "nvml":
            return self._get_info_nvml(device_id)
        
        return None
    
    def _get_info_nvidia_smi(self, device_id: int) -> Optional[GPUInfo]:
        """通过nvidia-smi获取GPU信息"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,power.draw",
                 f"--id={device_id}", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            parts = [p.strip() for p in result.stdout.strip().split(',')]
            if len(parts) >= 7:
                return GPUInfo(
                    device_id=device_id,
                    name=parts[0],
                    total_memory=int(float(parts[1])),
                    used_memory=int(float(parts[2])),
                    free_memory=int(float(parts[3])),
                    temperature=int(float(parts[4])),
                    utilization=int(float(parts[5])),
                    power_usage=float(parts[6])
                )
        except Exception as e:
            logger.debug(f"nvidia-smi获取信息失败: {e}")
        
        return None
    
    def _get_info_torch(self, device_id: int) -> Optional[GPUInfo]:
        """通过PyTorch获取GPU信息"""
        try:
            import torch
            
            if device_id >= torch.cuda.device_count():
                return None
            
            name = torch.cuda.get_device_name(device_id)
            props = torch.cuda.get_device_properties(device_id)
            total_mem = props.total_memory // (1024 * 1024)
            used_mem = torch.cuda.memory_allocated(device_id) // (1024 * 1024)
            free_mem = total_mem - used_mem
            
            return GPUInfo(
                device_id=device_id,
                name=name,
                total_memory=total_mem,
                used_memory=used_mem,
                free_memory=free_mem,
                temperature=0,
                utilization=0,
                power_usage=0.0,
                cuda_version=torch.version.cuda or ""
            )
        except Exception as e:
            logger.debug(f"PyTorch获取信息失败: {e}")
        
        return None
    
    def _get_info_nvml(self, device_id: int) -> Optional[GPUInfo]:
        """通过NVML获取GPU信息"""
        try:
            try:
                import nvidia_ml_py as nvml
            except ImportError:
                import pynvml as nvml
            
            handle = nvml.nvmlDeviceGetHandleByIndex(device_id)
            
            # 显存信息
            mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
            total_mem = mem_info.total // (1024 * 1024)
            used_mem = mem_info.used // (1024 * 1024)
            free_mem = mem_info.free // (1024 * 1024)
            
            # 温度
            try:
                temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
            except:
                temp = 0
            
            # 利用率
            try:
                util = nvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = util.gpu
            except:
                gpu_util = 0
            
            # 功耗
            try:
                power = nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
            except:
                power = 0.0
            
            # 名称
            name = nvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            
            # 驱动版本
            try:
                driver = nvml.nvmlSystemGetDriverVersion()
                if isinstance(driver, bytes):
                    driver = driver.decode('utf-8')
            except:
                driver = ""
            
            return GPUInfo(
                device_id=device_id,
                name=name,
                total_memory=total_mem,
                used_memory=used_mem,
                free_memory=free_mem,
                temperature=temp,
                utilization=gpu_util,
                power_usage=power,
                driver_version=driver
            )
        except Exception as e:
            logger.debug(f"NVML获取信息失败: {e}")
        
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
                    logger.error(f"回调函数执行失败: {e}")
            
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
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
    
    def get_detection_info(self) -> Dict:
        """获取检测信息"""
        return {
            "method": self._detection_method,
            "gpu_count": self.gpu_count,
            "gpu_names": self.gpu_names
        }


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
        f"  VRAM: {format_memory(info.used_memory)}/{format_memory(info.total_memory)} "
        f"({info.memory_usage_percent:.1f}%)\n"
        f"  Temp: {info.temperature}°C\n"
        f"  Util: {info.utilization}%\n"
        f"  Power: {info.power_usage:.1f}W"
    )
