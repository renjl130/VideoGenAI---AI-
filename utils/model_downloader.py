"""
模型下载管理器 - 支持断点续传、镜像源、进度显示
"""
import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import threading

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

try:
    from modelscope import snapshot_download as ms_snapshot_download
    MODELSOPE_AVAILABLE = True
except ImportError:
    MODELSOPE_AVAILABLE = False

from utils.logger import get_logger

logger = get_logger("model_downloader")


@dataclass
class ModelInfo:
    """模型信息"""
    model_id: str
    model_type: str  # t2v, i2v, vace
    model_size: str  # 1.3b, 14b
    resolution: str  # 480p, 720p
    repo_id: str
    description: str
    license: str
    vram_required: int  # GB
    download_size: int  # GB


# 支持的模型列表
SUPPORTED_MODELS = {
    "wan2.1-t2v-1.3b": ModelInfo(
        model_id="wan2.1-t2v-1.3b",
        model_type="t2v",
        model_size="1.3b",
        resolution="480p",
        repo_id="Wan-AI/Wan2.1-T2V-1.3B",
        description="Wan2.1 文本转视频 1.3B模型，适合消费级GPU",
        license="Apache-2.0",
        vram_required=8,
        download_size=5
    ),
    "wan2.1-t2v-14b": ModelInfo(
        model_id="wan2.1-t2v-14b",
        model_type="t2v",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-T2V-14B",
        description="Wan2.1 文本转视频 14B模型，最佳画质",
        license="Apache-2.0",
        vram_required=24,
        download_size=28
    ),
    "wan2.1-i2v-14b-720p": ModelInfo(
        model_id="wan2.1-i2v-14b-720p",
        model_type="i2v",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-I2V-14B-720P",
        description="Wan2.1 图片转视频 14B模型 720P",
        license="Apache-2.0",
        vram_required=24,
        download_size=28
    ),
    "wan2.1-i2v-14b-480p": ModelInfo(
        model_id="wan2.1-i2v-14b-480p",
        model_type="i2v",
        model_size="14b",
        resolution="480p",
        repo_id="Wan-AI/Wan2.1-I2V-14B-480P",
        description="Wan2.1 图片转视频 14B模型 480P",
        license="Apache-2.0",
        vram_required=16,
        download_size=28
    ),
    "wan2.1-flf2v-14b": ModelInfo(
        model_id="wan2.1-flf2v-14b",
        model_type="flf2v",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-FLF2V-14B-720P",
        description="Wan2.1 首尾帧转视频 14B模型",
        license="Apache-2.0",
        vram_required=24,
        download_size=28
    ),
    "wan2.1-vace-1.3b": ModelInfo(
        model_id="wan2.1-vace-1.3b",
        model_type="vace",
        model_size="1.3b",
        resolution="480p",
        repo_id="Wan-AI/Wan2.1-VACE-1.3B",
        description="Wan2.1 VACE视频编辑 1.3B模型",
        license="Apache-2.0",
        vram_required=8,
        download_size=5
    ),
    "wan2.1-vace-14b": ModelInfo(
        model_id="wan2.1-vace-14b",
        model_type="vace",
        model_size="14b",
        resolution="720p",
        repo_id="Wan-AI/Wan2.1-VACE-14B",
        description="Wan2.1 VACE视频编辑 14B模型",
        license="Apache-2.0",
        vram_required=24,
        download_size=28
    ),
    "cogvideox-2b": ModelInfo(
        model_id="cogvideox-2b",
        model_type="t2v",
        model_size="2b",
        resolution="480p",
        repo_id="THUDM/CogVideoX-2b",
        description="CogVideoX 2B模型，轻量级",
        license="Apache-2.0",
        vram_required=4,
        download_size=8
    ),
    "cogvideox-5b": ModelInfo(
        model_id="cogvideox-5b",
        model_type="t2v",
        model_size="5b",
        resolution="720p",
        repo_id="THUDM/CogVideoX-5b",
        description="CogVideoX 5B模型，高质量",
        license="CogVideoX LICENSE",
        vram_required=10,
        download_size=15
    ),
}


class DownloadProgress:
    """下载进度"""
    
    def __init__(self, model_id: str, total_size: int):
        self.model_id = model_id
        self.total_size = total_size
        self.downloaded_size = 0
        self.status = "pending"  # pending, downloading, completed, failed
        self.error = None
        self.start_time = None
        self.end_time = None
    
    @property
    def progress(self) -> float:
        """进度百分比"""
        if self.total_size == 0:
            return 0.0
        return (self.downloaded_size / self.total_size) * 100
    
    @property
    def speed(self) -> float:
        """下载速度 MB/s"""
        if not self.start_time or self.downloaded_size == 0:
            return 0.0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return (self.downloaded_size / 1024 / 1024) / elapsed
    
    @property
    def eta(self) -> int:
        """预计剩余时间（秒）"""
        if self.speed == 0:
            return 0
        remaining = self.total_size - self.downloaded_size
        return int(remaining / 1024 / 1024 / self.speed)


class ModelDownloader:
    """模型下载管理器"""
    
    _instance = None
    
    def __new__(cls, models_dir: str = "./models"):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, models_dir: str = "./models"):
        """初始化下载管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._models_dir = Path(models_dir)
        self._models_dir.mkdir(parents=True, exist_ok=True)
        
        self._downloads: Dict[str, DownloadProgress] = {}
        self._callbacks: List[Callable] = []
        self._download_threads: Dict[str, threading.Thread] = {}
        
        # 镜像源配置
        self._mirrors = {
            "huggingface": "https://huggingface.co",
            "hf-mirror": "https://hf-mirror.com",
            "modelscope": "modelscope"
        }
        self._current_mirror = "huggingface"
        
        # 扫描已下载的模型
        self._scan_downloaded_models()
    
    def _scan_downloaded_models(self):
        """扫描已下载的模型"""
        self._downloaded_models = {}
        
        for model_id, model_info in SUPPORTED_MODELS.items():
            model_path = self._models_dir / model_id
            if model_path.exists() and any(model_path.iterdir()):
                self._downloaded_models[model_id] = model_info
    
    def get_downloaded_models(self) -> Dict[str, ModelInfo]:
        """获取已下载的模型"""
        return self._downloaded_models.copy()
    
    def get_available_models(self) -> Dict[str, ModelInfo]:
        """获取所有可用模型"""
        return SUPPORTED_MODELS.copy()
    
    def is_model_downloaded(self, model_id: str) -> bool:
        """检查模型是否已下载"""
        return model_id in self._downloaded_models
    
    def get_model_path(self, model_id: str) -> Optional[Path]:
        """获取模型路径"""
        if model_id in self._downloaded_models:
            return self._models_dir / model_id
        return None
    
    def set_mirror(self, mirror: str):
        """设置镜像源"""
        if mirror in self._mirrors:
            self._current_mirror = mirror
            logger.info(f"切换镜像源到: {mirror}")
    
    def download_model(self, model_id: str, callback: Optional[Callable] = None) -> bool:
        """下载模型"""
        if model_id not in SUPPORTED_MODELS:
            logger.error(f"不支持的模型: {model_id}")
            return False
        
        if model_id in self._downloaded_models:
            logger.info(f"模型已存在: {model_id}")
            return True
        
        model_info = SUPPORTED_MODELS[model_id]
        
        # 创建下载进度
        progress = DownloadProgress(model_id, model_info.download_size * 1024 * 1024 * 1024)
        self._downloads[model_id] = progress
        
        # 添加回调
        if callback:
            self._callbacks.append(callback)
        
        # 在新线程中下载
        thread = threading.Thread(
            target=self._download_thread,
            args=(model_id, model_info),
            daemon=True
        )
        self._download_threads[model_id] = thread
        thread.start()
        
        return True
    
    def _download_thread(self, model_id: str, model_info: ModelInfo):
        """下载线程"""
        progress = self._downloads[model_id]
        progress.status = "downloading"
        progress.start_time = datetime.now()
        
        try:
            model_path = self._models_dir / model_id
            
            if self._current_mirror == "modelscope":
                self._download_from_modelscope(model_info.repo_id, str(model_path), progress)
            else:
                self._download_from_huggingface(model_info.repo_id, str(model_path), progress)
            
            progress.status = "completed"
            progress.end_time = datetime.now()
            progress.downloaded_size = progress.total_size
            
            # 更新已下载模型列表
            self._downloaded_models[model_id] = model_info
            
            logger.info(f"模型下载完成: {model_id}")
            
        except Exception as e:
            progress.status = "failed"
            progress.error = str(e)
            logger.error(f"模型下载失败: {model_id}, 错误: {e}")
        
        finally:
            # 通知回调
            for callback in self._callbacks:
                try:
                    callback(model_id, progress)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
    
    def _download_from_huggingface(self, repo_id: str, local_dir: str, progress: DownloadProgress):
        """从HuggingFace下载"""
        if not HF_HUB_AVAILABLE:
            raise ImportError("请安装 huggingface_hub: pip install huggingface_hub")
        
        # 设置镜像
        if self._current_mirror == "hf-mirror":
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            resume_download=True,  # 断点续传
            etag_timeout=30,
        )
    
    def _download_from_modelscope(self, repo_id: str, local_dir: str, progress: DownloadProgress):
        """从ModelScope下载"""
        if not MODELSOPE_AVAILABLE:
            raise ImportError("请安装 modelscope: pip install modelscope")
        
        ms_snapshot_download(
            model_id=repo_id,
            local_dir=local_dir,
        )
    
    def get_download_progress(self, model_id: str) -> Optional[DownloadProgress]:
        """获取下载进度"""
        return self._downloads.get(model_id)
    
    def get_all_downloads(self) -> Dict[str, DownloadProgress]:
        """获取所有下载任务"""
        return self._downloads.copy()
    
    def cancel_download(self, model_id: str):
        """取消下载（注意：可能无法立即停止）"""
        if model_id in self._downloads:
            self._downloads[model_id].status = "cancelled"
            logger.info(f"取消下载: {model_id}")
    
    def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        if model_id not in self._downloaded_models:
            return False
        
        model_path = self._models_dir / model_id
        if model_path.exists():
            shutil.rmtree(model_path)
            del self._downloaded_models[model_id]
            logger.info(f"删除模型: {model_id}")
            return True
        
        return False
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return SUPPORTED_MODELS.get(model_id)
    
    def add_callback(self, callback: Callable):
        """添加下载回调"""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除下载回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)


# 全局下载管理器实例
_downloader = None


def get_model_downloader(models_dir: str = "./models") -> ModelDownloader:
    """获取模型下载管理器实例"""
    global _downloader
    if _downloader is None:
        _downloader = ModelDownloader(models_dir)
    return _downloader
