"""
引擎基类 - 定义视频生成引擎的通用接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading


class EngineStatus(Enum):
    """引擎状态"""
    UNLOADED = "unloaded"      # 未加载
    LOADING = "loading"        # 加载中
    READY = "ready"            # 就绪
    GENERATING = "generating"  # 生成中
    ERROR = "error"            # 错误


@dataclass
class GenerationParams:
    """生成参数"""
    prompt: str
    negative_prompt: str = ""
    width: int = 832
    height: int = 480
    num_frames: int = 81
    fps: int = 16
    steps: int = 50
    cfg_scale: float = 5.0
    seed: int = -1
    
    # 图片/视频输入
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    first_frame_path: Optional[str] = None
    last_frame_path: Optional[str] = None
    
    # 优化参数
    precision: str = "auto"
    cpu_offload: bool = False
    sequential_offload: bool = False
    vae_tiling: bool = True
    attention_slicing: bool = False
    flash_attention: bool = True
    
    # 回调函数
    progress_callback: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "fps": self.fps,
            "steps": self.steps,
            "cfg_scale": self.cfg_scale,
            "seed": self.seed,
            "image_path": self.image_path,
            "video_path": self.video_path,
            "precision": self.precision,
            "cpu_offload": self.cpu_offload,
            "vae_tiling": self.vae_tiling
        }


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    duration: float = 0.0
    seed_used: int = -1
    metadata: Dict[str, Any] = None


class BaseEngine(ABC):
    """视频生成引擎基类"""
    
    def __init__(self, model_id: str):
        """初始化引擎"""
        self.model_id = model_id
        self.status = EngineStatus.UNLOADED
        self._model = None
        self._vae = None
        self._tokenizer = None
        self._lock = threading.Lock()
        
        # 回调函数
        self._on_status_change: List[Callable] = []
        self._on_progress: List[Callable] = []
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """引擎名称"""
        pass
    
    @property
    @abstractmethod
    def supported_tasks(self) -> List[str]:
        """支持的任务类型"""
        pass
    
    @property
    @abstractmethod
    def default_params(self) -> Dict[str, Any]:
        """默认参数"""
        pass
    
    @abstractmethod
    def load_model(self, model_path: str, **kwargs) -> bool:
        """加载模型"""
        pass
    
    @abstractmethod
    def unload_model(self):
        """卸载模型"""
        pass
    
    @abstractmethod
    def generate(self, params: GenerationParams) -> GenerationResult:
        """生成视频"""
        pass
    
    @abstractmethod
    def generate_t2v(self, params: GenerationParams) -> GenerationResult:
        """文本转视频"""
        pass
    
    @abstractmethod
    def generate_i2v(self, params: GenerationParams) -> GenerationResult:
        """图片转视频"""
        pass
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.status in [EngineStatus.READY, EngineStatus.GENERATING]
    
    def set_status(self, status: EngineStatus):
        """设置状态"""
        self.status = status
        for callback in self._on_status_change:
            try:
                callback(self.model_id, status)
            except Exception:
                pass
    
    def on_status_change(self, callback: Callable):
        """注册状态变化回调"""
        self._on_status_change.append(callback)
    
    def on_progress(self, callback: Callable):
        """注册进度回调"""
        self._on_progress.append(callback)
    
    def _report_progress(self, progress: float, message: str = ""):
        """报告进度"""
        for callback in self._on_progress:
            try:
                callback(self.model_id, progress, message)
            except Exception:
                pass
    
    def get_gpu_memory_usage(self) -> Dict[str, int]:
        """获取GPU显存使用情况"""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "allocated": torch.cuda.memory_allocated() // (1024 * 1024),
                    "cached": torch.cuda.memory_reserved() // (1024 * 1024),
                    "max_allocated": torch.cuda.max_memory_allocated() // (1024 * 1024)
                }
        except Exception:
            pass
        return {"allocated": 0, "cached": 0, "max_allocated": 0}
    
    def clear_cache(self):
        """清除GPU缓存"""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
