"""
GPU监控工具 - 实时监控GPU状态（使用nvidia-smi获取真实数据）
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
    """GPU监控器 - 使用nvidia-smi获取真实数据"""
    
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
        self._update_interval = 1.0
        
        # GPU信息
        self.gpu_count = 0
        self.gpu_names = []
        self._last_info: Dict[int, GPUInfo] = {}
        
        # 检测GPU
        self._detect_gpus()
    
    def _run_nvidia_smi(self, args: List[str]) -> Optional[str]:
        """运行nvidia-smi命令"""
        try:
            cmd = ["nvidia-smi"] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.debug(f"nvidia-smi failed: {result.stderr}")
                return None
        except FileNotFoundError:
            logger.debug("nvidia-smi not found")
            return None
        except subprocess.TimeoutExpired:
            logger.debug("nvidia-smi timeout")
            return None
        except Exception as e:
            logger.debug(f"nvidia-smi error: {e}")
            return None
    
    def _detect_gpus(self):
        """检测GPU"""
        logger.info("检测GPU...")
        
        # 使用nvidia-smi检测
        output = self._run_nvidia_smi([
            "--query-gpu=index,name,memory.total",
            "--format=csv,noheader,nounits"
        ])
        
        if output:
            lines = output.strip().split('\n')
            self.gpu_count = len(lines)
            self.gpu_names = []
            
            for line in lines:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    idx = int(parts[0])
                    name = parts[1]
                    self.gpu_names.append(name)
                    logger.info(f"GPU {idx}: {name}")
            
            if self.gpu_count > 0:
                logger.info(f"检测到 {self.gpu_count} 个GPU")
                return
        
        # 尝试PyTorch
        try:
            import torch
            if torch.cuda.is_available():
                self.gpu_count = torch.cuda.device_count()
                self.gpu_names = []
                for i in range(self.gpu_count):
                    name = torch.cuda.get_device_name(i)
                    self.gpu_names.append(name)
                    logger.info(f"GPU {i} (PyTorch): {name}")
                return
        except:
            pass
        
        logger.warning("未检测到GPU")
        self.gpu_count = 0
        self.gpu_names = []
    
    def get_gpu_info(self, device_id: int = 0) -> Optional[GPUInfo]:
        """获取GPU信息（实时）"""
        if device_id >= self.gpu_count:
            return None
        
        # 使用nvidia-smi获取实时数据
        output = self._run_nvidia_smi([
            "--query-gpu=index,name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,power.draw,driver_version",
            f"--id={device_id}",
            "--format=csv,noheader,nounits"
        ])
        
        if output:
            parts = [p.strip() for p in output.split(',')]
            if len(parts) >= 8:
                try:
                    info = GPUInfo(
                        device_id=int(parts[0]),
                        name=parts[1],
                        total_memory=int(float(parts[2])),
                        used_memory=int(float(parts[3])),
                        free_memory=int(float(parts[4])),
                        temperature=int(float(parts[5])),
                        utilization=int(float(parts[6])),
                        power_usage=float(parts[7]),
                        driver_version=parts[8] if len(parts) > 8 else ""
                    )
                    self._last_info[device_id] = info
                    return info
                except Exception as e:
                    logger.error(f"解析GPU信息失败: {e}")
        
        # 返回缓存的数据
        if device_id in self._last_info:
            return self._last_info[device_id]
        
        # 尝试PyTorch
        try:
            import torch
            if device_id < torch.cuda.device_count():
                name = torch.cuda.get_device_name(device_id)
                props = torch.cuda.get_device_properties(device_id)
                total_mem = props.total_memory // (1024 * 1024)
                used_mem = torch.cuda.memory_allocated(device_id) // (1024 * 1024)
                
                return GPUInfo(
                    device_id=device_id,
                    name=name,
                    total_memory=total_mem,
                    used_memory=used_mem,
                    free_memory=total_mem - used_mem,
                    temperature=0,
                    utilization=0,
                    power_usage=0.0
                )
        except:
            pass
        
        return None
    
    def get_all_gpu_info(self) -> List[GPUInfo]:
        """获取所有GPU信息"""
        infos = []
        
        # 使用nvidia-smi一次性获取所有GPU
        output = self._run_nvidia_smi([
            "--query-gpu=index,name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,power.draw",
            "--format=csv,noheader,nounits"
        ])
        
        if output:
            for line in output.strip().split('\n'):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 8:
                    try:
                        info = GPUInfo(
                            device_id=int(parts[0]),
                            name=parts[1],
                            total_memory=int(float(parts[2])),
                            used_memory=int(float(parts[3])),
                            free_memory=int(float(parts[4])),
                            temperature=int(float(parts[5])),
                            utilization=int(float(parts[6])),
                            power_usage=float(parts[7])
                        )
                        infos.append(info)
                        self._last_info[info.device_id] = info
                    except:
                        pass
        
        return infos
    
    def start_monitoring(self, interval: float = 1.0):
        """开始监控"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._update_interval = interval
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"GPU监控已启动，间隔 {interval} 秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        logger.info("GPU监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._monitoring:
            # 获取最新信息
            self.get_all_gpu_info()
            
            # 调用回调
            for callback in self._callbacks:
                try:
                    callback(list(self._last_info.values()))
                except Exception as e:
                    logger.error(f"回调失败: {e}")
            
            time.sleep(self._update_interval)
    
    def add_callback(self, callback: Callable):
        """添加回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def clear_cache(self):
        """清除GPU缓存"""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("GPU缓存已清除")
        except:
            pass
    
    def get_detection_info(self) -> Dict:
        """获取检测信息"""
        return {
            "gpu_count": self.gpu_count,
            "gpu_names": self.gpu_names
        }


# 全局实例
gpu_monitor = GPUMonitor()


def get_gpu_monitor() -> GPUMonitor:
    """获取GPU监控实例"""
    return gpu_monitor


def format_memory(mb: int) -> str:
    """格式化显存"""
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb} MB"


def format_gpu_info(info: GPUInfo) -> str:
    """格式化GPU信息"""
    return (
        f"GPU {info.device_id}: {info.name}\n"
        f"  显存: {format_memory(info.used_memory)}/{format_memory(info.total_memory)} ({info.memory_usage_percent:.1f}%)\n"
        f"  温度: {info.temperature}°C\n"
        f"  利用率: {info.utilization}%\n"
        f"  功耗: {info.power_usage:.1f}W"
    )
