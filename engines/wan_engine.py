"""
Wan2.1 视频生成引擎 - 基于 Diffusers 实现
"""
import os
import time
import gc
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading

import torch
import numpy as np

from engines.base_engine import BaseEngine, EngineStatus, GenerationParams, GenerationResult
from utils.logger import get_logger

logger = get_logger("wan_engine")


class WanEngine(BaseEngine):
    """Wan2.1 视频生成引擎"""
    
    def __init__(self, model_id: str = "wan2.1-t2v-1.3b"):
        """初始化Wan引擎"""
        super().__init__(model_id)
        
        self._pipe = None
        self._vae = None
        self._text_encoder = None
        self._transformer = None
        self._scheduler = None
        self._image_encoder = None
        
        # 模型配置
        self._model_config = {
            "wan2.1-t2v-1.3b": {
                "repo_id": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
                "task": "t2v",
                "resolution": "480p",
                "default_frames": 81,
                "flow_shift": 3.0
            },
            "wan2.1-t2v-14b": {
                "repo_id": "Wan-AI/Wan2.1-T2V-14B-Diffusers",
                "task": "t2v",
                "resolution": "720p",
                "default_frames": 81,
                "flow_shift": 5.0
            },
            "wan2.1-i2v-14b-720p": {
                "repo_id": "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers",
                "task": "i2v",
                "resolution": "720p",
                "default_frames": 81,
                "flow_shift": 5.0
            },
            "wan2.1-i2v-14b-480p": {
                "repo_id": "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
                "task": "i2v",
                "resolution": "480p",
                "default_frames": 81,
                "flow_shift": 3.0
            }
        }
        
        self._current_config = self._model_config.get(model_id, self._model_config["wan2.1-t2v-1.3b"])
    
    @property
    def engine_name(self) -> str:
        """引擎名称"""
        return "Wan2.1"
    
    @property
    def supported_tasks(self) -> List[str]:
        """支持的任务类型"""
        return ["t2v", "i2v", "flf2v"]
    
    @property
    def default_params(self) -> Dict[str, Any]:
        """默认参数"""
        return {
            "width": 832,
            "height": 480,
            "num_frames": self._current_config["default_frames"],
            "fps": 16,
            "steps": 50,
            "cfg_scale": 5.0,
            "seed": -1
        }
    
    def load_model(self, model_path: str, **kwargs) -> bool:
        """加载模型"""
        with self._lock:
            if self.status == EngineStatus.LOADING:
                logger.warning("模型正在加载中")
                return False
            
            self.set_status(EngineStatus.LOADING)
            logger.info(f"开始加载模型: {model_path}")
            
            try:
                # 检查路径
                if not os.path.exists(model_path):
                    # 尝试从HuggingFace下载
                    model_id = self.model_id
                    if model_id in self._model_config:
                        model_path = self._model_config[model_id]["repo_id"]
                    else:
                        raise FileNotFoundError(f"模型路径不存在: {model_path}")
                
                # 获取配置
                precision = kwargs.get("precision", "auto")
                cpu_offload = kwargs.get("cpu_offload", False)
                vae_tiling = kwargs.get("vae_tiling", True)
                
                # 设置精度
                if precision == "auto":
                    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                elif precision == "bf16":
                    dtype = torch.bfloat16
                elif precision == "fp16":
                    dtype = torch.float16
                else:
                    dtype = torch.float32
                
                # 导入diffusers
                from diffusers import AutoencoderKLWan, WanPipeline, WanImageToVideoPipeline
                from diffusers.schedulers.scheduling_unipc_multistep import UniPCMultistepScheduler
                from transformers import CLIPVisionModel
                
                # 加载VAE
                logger.info("加载VAE...")
                self._vae = AutoencoderKLWan.from_pretrained(
                    model_path,
                    subfolder="vae",
                    torch_dtype=torch.float32
                )
                
                # 配置调度器
                flow_shift = self._current_config.get("flow_shift", 3.0)
                scheduler = UniPCMultistepScheduler(
                    prediction_type='flow_prediction',
                    use_flow_sigmas=True,
                    num_train_timesteps=1000,
                    flow_shift=flow_shift
                )
                
                # 根据任务类型加载不同的Pipeline
                task = self._current_config.get("task", "t2v")
                
                if task == "t2v":
                    logger.info("加载T2V Pipeline...")
                    self._pipe = WanPipeline.from_pretrained(
                        model_path,
                        vae=self._vae,
                        torch_dtype=dtype
                    )
                elif task == "i2v":
                    logger.info("加载I2V Pipeline...")
                    self._image_encoder = CLIPVisionModel.from_pretrained(
                        model_path,
                        subfolder="image_encoder",
                        torch_dtype=torch.float32
                    )
                    self._pipe = WanImageToVideoPipeline.from_pretrained(
                        model_path,
                        vae=self._vae,
                        image_encoder=self._image_encoder,
                        torch_dtype=dtype
                    )
                
                # 设置调度器
                self._pipe.scheduler = scheduler
                
                # 应用优化
                self._apply_optimizations(cpu_offload, vae_tiling, kwargs)
                
                # 移动到GPU
                if not cpu_offload:
                    self._pipe.to("cuda")
                
                self.set_status(EngineStatus.READY)
                logger.info("模型加载完成")
                return True
                
            except Exception as e:
                logger.error(f"模型加载失败: {e}")
                self.set_status(EngineStatus.ERROR)
                return False
    
    def _apply_optimizations(self, cpu_offload: bool, vae_tiling: bool, kwargs: Dict):
        """应用优化设置"""
        try:
            # CPU Offload
            if cpu_offload:
                logger.info("启用CPU Offload")
                self._pipe.enable_sequential_cpu_offload()
            
            # VAE Tiling
            if vae_tiling:
                logger.info("启用VAE Tiling")
                self._pipe.vae.enable_tiling()
            
            # Attention Slicing
            if kwargs.get("attention_slicing", False):
                logger.info("启用Attention Slicing")
                self._pipe.enable_attention_slicing()
            
            # VAE Slicing
            if kwargs.get("vae_slicing", True):
                self._pipe.vae.enable_slicing()
            
            # xFormers
            if kwargs.get("xformers", False):
                try:
                    self._pipe.enable_xformers_memory_efficient_attention()
                    logger.info("启用xFormers")
                except Exception as e:
                    logger.warning(f"xFormers不可用: {e}")
            
            # Torch Compile
            if kwargs.get("torch_compile", False):
                try:
                    self._pipe.transformer = torch.compile(
                        self._pipe.transformer,
                        mode="reduce-overhead",
                        fullgraph=True
                    )
                    logger.info("启用Torch Compile")
                except Exception as e:
                    logger.warning(f"Torch Compile失败: {e}")
            
            # Flash Attention
            if kwargs.get("flash_attention", True):
                try:
                    if hasattr(self._pipe.transformer, 'enable_flash_attention'):
                        self._pipe.transformer.enable_flash_attention()
                        logger.info("启用Flash Attention")
                except Exception:
                    pass
            
        except Exception as e:
            logger.warning(f"应用优化失败: {e}")
    
    def unload_model(self):
        """卸载模型"""
        with self._lock:
            logger.info("卸载模型...")
            
            self._pipe = None
            self._vae = None
            self._text_encoder = None
            self._transformer = None
            self._scheduler = None
            self._image_encoder = None
            
            # 清除GPU缓存
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.set_status(EngineStatus.UNLOADED)
            logger.info("模型已卸载")
    
    def generate(self, params: GenerationParams) -> GenerationResult:
        """生成视频"""
        if not self.is_loaded():
            return GenerationResult(
                success=False,
                error_message="模型未加载"
            )
        
        # 根据任务类型调用不同的生成方法
        task = self._current_config.get("task", "t2v")
        
        if task == "t2v":
            return self.generate_t2v(params)
        elif task == "i2v":
            return self.generate_i2v(params)
        else:
            return GenerationResult(
                success=False,
                error_message=f"不支持的任务类型: {task}"
            )
    
    def generate_t2v(self, params: GenerationParams) -> GenerationResult:
        """文本转视频"""
        self.set_status(EngineStatus.GENERATING)
        start_time = time.time()
        
        try:
            # 处理种子
            seed = params.seed
            if seed == -1:
                seed = random.randint(0, 2**32 - 1)
            
            generator = torch.Generator(device="cuda").manual_seed(seed)
            
            logger.info(f"开始生成T2V视频，种子: {seed}")
            
            # 进度回调
            def progress_callback(step, timestep, latents):
                if params.progress_callback:
                    progress = (step / params.steps) * 100
                    params.progress_callback(progress, f"步骤 {step}/{params.steps}")
            
            # 生成视频
            output = self._pipe(
                prompt=params.prompt,
                negative_prompt=params.negative_prompt,
                height=params.height,
                width=params.width,
                num_frames=params.num_frames,
                guidance_scale=params.cfg_scale,
                num_inference_steps=params.steps,
                generator=generator,
                callback_on_step_end=progress_callback
            )
            
            # 保存视频
            output_dir = Path("./outputs")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"t2v_{timestamp}_{seed}.mp4"
            
            from diffusers.utils import export_to_video
            video = output.frames[0]
            export_to_video(video, str(output_path), fps=params.fps)
            
            duration = time.time() - start_time
            
            self.set_status(EngineStatus.READY)
            logger.info(f"视频生成完成，耗时: {duration:.1f}秒")
            
            return GenerationResult(
                success=True,
                output_path=str(output_path),
                duration=duration,
                seed_used=seed,
                metadata={
                    "width": params.width,
                    "height": params.height,
                    "frames": params.num_frames,
                    "fps": params.fps
                }
            )
            
        except Exception as e:
            logger.error(f"T2V生成失败: {e}")
            self.set_status(EngineStatus.READY)
            return GenerationResult(
                success=False,
                error_message=str(e)
            )
    
    def generate_i2v(self, params: GenerationParams) -> GenerationResult:
        """图片转视频"""
        self.set_status(EngineStatus.GENERATING)
        start_time = time.time()
        
        try:
            # 检查输入图片
            if not params.image_path or not os.path.exists(params.image_path):
                return GenerationResult(
                    success=False,
                    error_message="输入图片不存在"
                )
            
            # 处理种子
            seed = params.seed
            if seed == -1:
                seed = random.randint(0, 2**32 - 1)
            
            generator = torch.Generator(device="cuda").manual_seed(seed)
            
            logger.info(f"开始生成I2V视频，种子: {seed}")
            
            # 加载图片
            from diffusers.utils import load_image
            import numpy as np
            
            image = load_image(params.image_path)
            
            # 计算尺寸
            max_area = params.height * params.width
            aspect_ratio = image.height / image.width
            mod_value = self._pipe.vae_scale_factor_spatial * self._pipe.transformer.config.patch_size[1]
            height = round(np.sqrt(max_area * aspect_ratio)) // mod_value * mod_value
            width = round(np.sqrt(max_area / aspect_ratio)) // mod_value * mod_value
            image = image.resize((width, height))
            
            # 进度回调
            def progress_callback(step, timestep, latents):
                if params.progress_callback:
                    progress = (step / params.steps) * 100
                    params.progress_callback(progress, f"步骤 {step}/{params.steps}")
            
            # 生成视频
            output = self._pipe(
                image=image,
                prompt=params.prompt,
                negative_prompt=params.negative_prompt,
                height=height,
                width=width,
                num_frames=params.num_frames,
                guidance_scale=params.cfg_scale,
                num_inference_steps=params.steps,
                generator=generator,
                callback_on_step_end=progress_callback
            )
            
            # 保存视频
            output_dir = Path("./outputs")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"i2v_{timestamp}_{seed}.mp4"
            
            from diffusers.utils import export_to_video
            video = output.frames[0]
            export_to_video(video, str(output_path), fps=params.fps)
            
            duration = time.time() - start_time
            
            self.set_status(EngineStatus.READY)
            logger.info(f"视频生成完成，耗时: {duration:.1f}秒")
            
            return GenerationResult(
                success=True,
                output_path=str(output_path),
                duration=duration,
                seed_used=seed,
                metadata={
                    "width": width,
                    "height": height,
                    "frames": params.num_frames,
                    "fps": params.fps,
                    "input_image": params.image_path
                }
            )
            
        except Exception as e:
            logger.error(f"I2V生成失败: {e}")
            self.set_status(EngineStatus.READY)
            return GenerationResult(
                success=False,
                error_message=str(e)
            )
    
    def switch_model(self, model_id: str, **kwargs) -> bool:
        """切换模型"""
        if model_id not in self._model_config:
            logger.error(f"不支持的模型: {model_id}")
            return False
        
        # 卸载当前模型
        self.unload_model()
        
        # 更新配置
        self.model_id = model_id
        self._current_config = self._model_config[model_id]
        
        # 加载新模型
        model_path = kwargs.get("model_path", self._current_config["repo_id"])
        return self.load_model(model_path, **kwargs)


# 全局引擎管理器
class EngineManager:
    """引擎管理器"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化引擎管理器"""
        if self._initialized:
            return
            
        self._initialized = True
        self._engines: Dict[str, BaseEngine] = {}
        self._active_engine: Optional[BaseEngine] = None
    
    def register_engine(self, engine: BaseEngine):
        """注册引擎"""
        self._engines[engine.model_id] = engine
        logger.info(f"注册引擎: {engine.engine_name} ({engine.model_id})")
    
    def get_engine(self, model_id: str) -> Optional[BaseEngine]:
        """获取引擎"""
        return self._engines.get(model_id)
    
    def get_active_engine(self) -> Optional[BaseEngine]:
        """获取当前活跃引擎"""
        return self._active_engine
    
    def set_active_engine(self, model_id: str) -> bool:
        """设置活跃引擎"""
        engine = self._engines.get(model_id)
        if engine:
            self._active_engine = engine
            logger.info(f"切换活跃引擎: {model_id}")
            return True
        return False
    
    def load_model(self, model_id: str, model_path: str, **kwargs) -> bool:
        """加载模型"""
        engine = self._engines.get(model_id)
        if not engine:
            # 创建新引擎
            engine = WanEngine(model_id)
            self.register_engine(engine)
        
        success = engine.load_model(model_path, **kwargs)
        if success:
            self._active_engine = engine
        return success
    
    def unload_all(self):
        """卸载所有模型"""
        for engine in self._engines.values():
            engine.unload_model()
        self._active_engine = None
    
    def get_loaded_engines(self) -> List[BaseEngine]:
        """获取已加载的引擎"""
        return [e for e in self._engines.values() if e.is_loaded()]


# 全局引擎管理器实例
_engine_manager = None


def get_engine_manager() -> EngineManager:
    """获取引擎管理器实例"""
    global _engine_manager
    if _engine_manager is None:
        _engine_manager = EngineManager()
    return _engine_manager
