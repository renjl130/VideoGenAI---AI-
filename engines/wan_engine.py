"""
Wan2.1 视频生成引擎 - 基于 Diffusers 实现
"""

import gc
import os
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, ClassVar

import torch

from engines.base_engine import (
    BaseEngine,
    EngineStatus,
    GenerationCancelledError,
    GenerationParams,
    GenerationResult,
)
from utils.generation_validation import (
    GenerationRequestValues,
    GenerationValidationError,
    validate_generation_request,
)
from utils.inference_errors import classify_inference_error
from utils.logger import get_logger
from utils.output_naming import reserved_output_path
from utils.paths import APP_PATHS, resolve_project_path
from utils.scheduler_registry import SchedulerType, create_wan_scheduler

logger = get_logger("wan_engine")


class WanEngine(BaseEngine):
    """Wan2.1 视频生成引擎"""

    def __init__(self, model_id: str = "wan2.1-t2v-1.3b"):
        """初始化Wan引擎"""
        super().__init__(model_id)

        # Diffusers components are imported lazily; Any is the explicit boundary
        # for third-party pipeline classes that vary by task and library version.
        self._pipe: Any = None
        self._vae: Any = None
        self._text_encoder: Any = None
        self._transformer: Any = None
        self._scheduler: Any = None
        self._scheduler_type = SchedulerType.UNIPC
        self._active_lora_id: str | None = None
        self._active_lora_scale = 1.0
        self._image_encoder: Any = None
        self._device = "cuda:0"
        self._device_id = 0
        self._last_error_report: dict[str, Any] | None = None

        # 模型配置
        self._model_config: dict[str, dict[str, Any]] = {
            "wan2.1-t2v-1.3b": {
                "repo_id": "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
                "task": "t2v",
                "resolution": "480p",
                "default_frames": 81,
                "flow_shift": 3.0,
            },
            "wan2.1-t2v-14b": {
                "repo_id": "Wan-AI/Wan2.1-T2V-14B-Diffusers",
                "task": "t2v",
                "resolution": "720p",
                "default_frames": 81,
                "flow_shift": 5.0,
            },
            "wan2.1-i2v-14b-720p": {
                "repo_id": "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers",
                "task": "i2v",
                "resolution": "720p",
                "default_frames": 81,
                "flow_shift": 5.0,
            },
            "wan2.1-i2v-14b-480p": {
                "repo_id": "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
                "task": "i2v",
                "resolution": "480p",
                "default_frames": 81,
                "flow_shift": 3.0,
            },
        }

        self._current_config = self._model_config.get(
            model_id, self._model_config["wan2.1-t2v-1.3b"]
        )

    @property
    def engine_name(self) -> str:
        """引擎名称"""
        return "Wan2.1"

    @property
    def last_error_report(self) -> dict[str, Any] | None:
        """Return the most recent structured load or generation error."""
        return dict(self._last_error_report) if self._last_error_report else None

    @property
    def supported_tasks(self) -> list[str]:
        """支持的任务类型"""
        return ["t2v", "i2v", "flf2v"]

    @property
    def default_params(self) -> dict[str, Any]:
        """默认参数"""
        return {
            "width": 832,
            "height": 480,
            "num_frames": self._current_config["default_frames"],
            "fps": 16,
            "steps": 50,
            "cfg_scale": 5.0,
            "seed": -1,
        }

    def load_model(self, model_path: str, **kwargs) -> bool:
        """加载模型"""
        with self._lock:
            if self.status == EngineStatus.LOADING:
                logger.warning("模型正在加载中")
                return False

            self.set_status(EngineStatus.LOADING)
            self._last_error_report = None
            logger.info(f"开始加载模型: {model_path}")

            try:
                if not torch.cuda.is_available():
                    raise RuntimeError(
                        "当前 PyTorch 不支持 CUDA。请安装与 NVIDIA 驱动匹配的 "
                        "CUDA 版 PyTorch 后再加载模型。"
                    )

                device_id = int(kwargs.get("device_id", 0))
                if device_id < 0 or device_id >= torch.cuda.device_count():
                    raise ValueError(f"无效的 CUDA 设备编号: {device_id}")
                self._device = f"cuda:{device_id}"
                self._device_id = device_id

                # 检查路径
                if not os.path.exists(model_path):
                    # 尝试从HuggingFace下载
                    model_id = self.model_id
                    if model_id in self._model_config:
                        model_path = str(self._model_config[model_id]["repo_id"])
                    else:
                        raise FileNotFoundError(f"模型路径不存在: {model_path}")

                # 获取配置
                precision = kwargs.get("precision", "auto")
                cpu_offload = kwargs.get("cpu_offload", False)
                sequential_offload = kwargs.get("sequential_offload", False)
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
                from diffusers import AutoencoderKLWan, WanImageToVideoPipeline, WanPipeline
                from transformers import CLIPVisionModel

                # 加载VAE
                logger.info("加载VAE...")
                self._vae = AutoencoderKLWan.from_pretrained(
                    model_path, subfolder="vae", torch_dtype=torch.float32
                )

                # Resolve a validated scheduler; UniPC remains the compatibility default.
                flow_shift = float(self._current_config.get("flow_shift", 3.0))
                self._scheduler_type = SchedulerType.parse(
                    str(kwargs.get("scheduler", SchedulerType.UNIPC.value))
                )
                scheduler = create_wan_scheduler(self._scheduler_type, flow_shift)
                self._scheduler = scheduler
                logger.info("Scheduler: %s", self._scheduler_type.value)

                # 根据任务类型加载不同的Pipeline
                task = self._current_config.get("task", "t2v")

                if task == "t2v":
                    logger.info("加载T2V Pipeline...")
                    self._pipe = WanPipeline.from_pretrained(
                        model_path, vae=self._vae, torch_dtype=dtype
                    )
                elif task == "i2v":
                    logger.info("加载I2V Pipeline...")
                    self._image_encoder = CLIPVisionModel.from_pretrained(
                        model_path, subfolder="image_encoder", torch_dtype=torch.float32
                    )
                    self._pipe = WanImageToVideoPipeline.from_pretrained(
                        model_path,
                        vae=self._vae,
                        image_encoder=self._image_encoder,
                        torch_dtype=dtype,
                    )

                # 设置调度器
                self._pipe.scheduler = scheduler

                self._apply_lora(
                    lora_id=str(kwargs.get("lora_id", "") or ""),
                    lora_path=str(kwargs.get("lora_path", "") or ""),
                    adapter_name=str(kwargs.get("lora_adapter_name", "") or ""),
                    scale=float(kwargs.get("lora_scale", 1.0)),
                )

                # 应用优化
                optimization_options = dict(kwargs)
                optimization_options["sequential_offload"] = sequential_offload
                self._apply_optimizations(
                    cpu_offload,
                    vae_tiling,
                    optimization_options,
                )

                # 移动到GPU
                if not cpu_offload and not sequential_offload:
                    self._pipe.to(self._device)

                self.set_status(EngineStatus.READY)
                logger.info("模型加载完成")
                return True

            except Exception as error:
                report = classify_inference_error(
                    error,
                    phase="model_load",
                    device_id=self._device_id,
                )
                self._last_error_report = report.to_dict()
                logger.exception(
                    "Model load failed [%s]: %s",
                    report.kind.value,
                    report.user_message,
                )
                self._release_model_resources(clear_error=False)
                self.set_status(EngineStatus.ERROR)
                return False

    def _apply_lora(
        self,
        *,
        lora_id: str,
        lora_path: str,
        adapter_name: str,
        scale: float,
    ) -> None:
        """Load one validated Wan LoRA and activate it at the requested strength."""
        if not lora_id:
            self._active_lora_id = None
            self._active_lora_scale = 1.0
            return
        if not lora_path or not adapter_name:
            raise ValueError("Resolved LoRA path and adapter name are required")
        if not 0.0 < scale <= 2.0:
            raise ValueError("LoRA scale must be greater than 0 and at most 2")

        try:
            import peft  # noqa: F401
        except ImportError as error:
            raise RuntimeError(
                "LoRA support requires the PEFT package; install project dependencies first"
            ) from error

        if not hasattr(self._pipe, "load_lora_weights") or not hasattr(self._pipe, "set_adapters"):
            raise RuntimeError("The active Diffusers Wan pipeline does not support LoRA adapters")
        self._pipe.load_lora_weights(lora_path, adapter_name=adapter_name)
        self._pipe.set_adapters(adapter_name, adapter_weights=scale)
        self._active_lora_id = lora_id
        self._active_lora_scale = scale
        logger.info("Loaded LoRA %s at scale %.3f", lora_id, scale)

    def unload_lora(self) -> bool:
        """Unload active LoRA weights without unloading the base model."""
        with self._lock:
            if self.status is EngineStatus.GENERATING:
                logger.error("Cannot unload LoRA while generation is running")
                return False
            if self._pipe is not None and self._active_lora_id:
                self._pipe.unload_lora_weights()
            self._active_lora_id = None
            self._active_lora_scale = 1.0
            return True

    def _apply_optimizations(
        self,
        cpu_offload: bool,
        vae_tiling: bool,
        kwargs: dict[str, Any],
    ) -> None:
        """Apply requested optimizations without silently disabling required offload.

        Sequential/model CPU offload is the primary low-VRAM safety mechanism.  If it
        cannot be enabled, continuing with a fully GPU-resident pipeline can turn a
        recoverable setup problem into a CUDA out-of-memory failure during generation.
        Optional accelerators remain best-effort and do not prevent model use.
        """
        if self._pipe is None:
            raise RuntimeError("Cannot apply optimizations before a pipeline is created")

        if kwargs.get("sequential_offload", False):
            try:
                logger.info("Enabling sequential CPU offload")
                self._pipe.enable_sequential_cpu_offload()
            except Exception as error:
                raise RuntimeError(
                    "Sequential CPU offload was requested but could not be enabled. "
                    "Install compatible Accelerate/Diffusers dependencies or choose "
                    "a profile that fits available VRAM."
                ) from error
        elif cpu_offload:
            try:
                logger.info("Enabling model CPU offload")
                self._pipe.enable_model_cpu_offload()
            except Exception as error:
                raise RuntimeError(
                    "Model CPU offload was requested but could not be enabled. "
                    "Install compatible Accelerate/Diffusers dependencies or choose "
                    "a profile that fits available VRAM."
                ) from error

        if vae_tiling:
            try:
                self._pipe.vae.enable_tiling()
                logger.info("Enabled VAE tiling")
            except Exception as error:
                logger.warning("Could not enable VAE tiling: %s", error)

        if kwargs.get("attention_slicing", False):
            try:
                self._pipe.enable_attention_slicing()
                logger.info("Enabled attention slicing")
            except Exception as error:
                logger.warning("Could not enable attention slicing: %s", error)

        if kwargs.get("vae_slicing", True):
            try:
                self._pipe.vae.enable_slicing()
                logger.info("Enabled VAE slicing")
            except Exception as error:
                logger.warning("Could not enable VAE slicing: %s", error)

        if kwargs.get("xformers", False):
            try:
                self._pipe.enable_xformers_memory_efficient_attention()
                logger.info("Enabled xFormers attention")
            except Exception as error:
                logger.warning("xFormers is unavailable: %s", error)

        if kwargs.get("torch_compile", False):
            try:
                self._pipe.transformer = torch.compile(
                    self._pipe.transformer,
                    mode="reduce-overhead",
                    fullgraph=True,
                )
                logger.info("Enabled torch.compile")
            except Exception as error:
                logger.warning("torch.compile could not be enabled: %s", error)

        if kwargs.get("flash_attention", True) and hasattr(
            self._pipe.transformer,
            "enable_flash_attention",
        ):
            try:
                self._pipe.transformer.enable_flash_attention()
                logger.info("Enabled Flash Attention")
            except Exception as error:
                logger.warning("Flash Attention could not be enabled: %s", error)

    def _release_model_resources(self, *, clear_error: bool = True):
        """释放模型引用和 CUDA 缓存，不改变引擎状态。"""
        self._pipe = None
        self._active_lora_id = None
        self._active_lora_scale = 1.0
        self._vae = None
        self._text_encoder = None
        self._transformer = None
        self._scheduler = None
        self._image_encoder = None
        if clear_error:
            self._last_error_report = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _create_progress_callback(self, params: GenerationParams):
        """创建符合 Diffusers callback_on_step_end 协议的回调。"""
        total_steps = max(params.steps, 1)

        def callback(_pipe, step, _timestep, callback_kwargs):
            if params.cancellation_callback and params.cancellation_callback():
                raise GenerationCancelledError("任务已取消")
            progress = min(((step + 1) / total_steps) * 100, 100.0)
            message = f"步骤 {step + 1}/{total_steps}"
            if params.progress_callback:
                params.progress_callback(progress, message)
            self._report_progress(progress, message)
            return callback_kwargs

        return callback

    def unload_model(self):
        """卸载模型"""
        with self._lock:
            logger.info("卸载模型...")

            self._release_model_resources()

            self.set_status(EngineStatus.UNLOADED)
            logger.info("模型已卸载")

    def generate(self, params: GenerationParams) -> GenerationResult:
        """生成视频"""
        if not self.is_loaded():
            return GenerationResult(success=False, error_message="模型未加载")

        # 根据任务类型调用不同的生成方法
        task = str(self._current_config.get("task", "t2v"))
        task_type = "image_to_video" if task == "i2v" else "text_to_video"
        try:
            validate_generation_request(
                GenerationRequestValues(
                    prompt=params.prompt,
                    width=params.width,
                    height=params.height,
                    num_frames=params.num_frames,
                    fps=params.fps,
                    steps=params.steps,
                    cfg_scale=params.cfg_scale,
                    seed=params.seed,
                    task_type=task_type,
                    image_path=params.image_path,
                )
            )
        except GenerationValidationError as error:
            return GenerationResult(success=False, error_message=str(error))

        if task == "t2v":
            return self.generate_t2v(params)
        elif task == "i2v":
            return self.generate_i2v(params)
        else:
            return GenerationResult(success=False, error_message=f"不支持的任务类型: {task}")

    def generate_t2v(self, params: GenerationParams) -> GenerationResult:
        """文本转视频"""
        self.set_status(EngineStatus.GENERATING)
        self._last_error_report = None
        start_time = time.time()

        try:
            if params.cancellation_callback and params.cancellation_callback():
                raise GenerationCancelledError("任务已取消")

            # 处理种子
            seed = params.seed
            if seed == -1:
                seed = random.randint(0, 2**32 - 1)

            generator = torch.Generator(device=self._device).manual_seed(seed)

            logger.info(f"开始生成T2V视频，种子: {seed}")

            progress_callback = self._create_progress_callback(params)

            # 生成视频
            with torch.inference_mode():
                output = self._pipe(
                    prompt=params.prompt,
                    negative_prompt=params.negative_prompt,
                    height=params.height,
                    width=params.width,
                    num_frames=params.num_frames,
                    guidance_scale=params.cfg_scale,
                    num_inference_steps=params.steps,
                    generator=generator,
                    callback_on_step_end=progress_callback,
                )

            # 保存视频
            output_dir = (
                resolve_project_path(params.output_dir) if params.output_dir else APP_PATHS.outputs
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            from diffusers.utils import export_to_video

            video = output.frames[0]
            with reserved_output_path(
                output_dir,
                params.output_filename_pattern,
                model_id=self.model_id,
                seed=seed,
                task="t2v",
                task_id=params.task_id,
            ) as output_path:
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
                    "fps": params.fps,
                },
            )

        except Exception as error:
            report = classify_inference_error(
                error,
                phase="t2v_generation",
                device_id=self._device_id,
            )
            self._last_error_report = report.to_dict()
            logger.exception(
                "Generation failed [%s]: %s",
                report.kind.value,
                report.user_message,
            )
            self.set_status(EngineStatus.READY)
            return GenerationResult(
                success=False,
                error_message=report.user_message,
                error_report=report.to_dict(),
            )

    def generate_i2v(self, params: GenerationParams) -> GenerationResult:
        """图片转视频"""
        if not params.image_path or not os.path.exists(params.image_path):
            return GenerationResult(
                success=False,
                error_message="输入图片不存在",
            )

        self.set_status(EngineStatus.GENERATING)
        self._last_error_report = None
        start_time = time.time()

        try:
            if params.cancellation_callback and params.cancellation_callback():
                raise GenerationCancelledError("任务已取消")

            # 处理种子
            seed = params.seed
            if seed == -1:
                seed = random.randint(0, 2**32 - 1)

            generator = torch.Generator(device=self._device).manual_seed(seed)

            logger.info(f"开始生成I2V视频，种子: {seed}")

            # 加载图片
            import numpy as np
            from diffusers.utils import load_image

            image = load_image(params.image_path)

            # 计算尺寸
            max_area = params.height * params.width
            aspect_ratio = image.height / image.width
            mod_value = (
                self._pipe.vae_scale_factor_spatial * self._pipe.transformer.config.patch_size[1]
            )
            height = round(np.sqrt(max_area * aspect_ratio)) // mod_value * mod_value
            width = round(np.sqrt(max_area / aspect_ratio)) // mod_value * mod_value
            image = image.resize((width, height))

            progress_callback = self._create_progress_callback(params)

            # 生成视频
            with torch.inference_mode():
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
                    callback_on_step_end=progress_callback,
                )

            # 保存视频
            output_dir = (
                resolve_project_path(params.output_dir) if params.output_dir else APP_PATHS.outputs
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            from diffusers.utils import export_to_video

            video = output.frames[0]
            with reserved_output_path(
                output_dir,
                params.output_filename_pattern,
                model_id=self.model_id,
                seed=seed,
                task="i2v",
                task_id=params.task_id,
            ) as output_path:
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
                    "input_image": params.image_path,
                },
            )

        except Exception as error:
            report = classify_inference_error(
                error,
                phase="i2v_generation",
                device_id=self._device_id,
            )
            self._last_error_report = report.to_dict()
            logger.exception(
                "Generation failed [%s]: %s",
                report.kind.value,
                report.user_message,
            )
            self.set_status(EngineStatus.READY)
            return GenerationResult(
                success=False,
                error_message=report.user_message,
                error_report=report.to_dict(),
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
        model_path = str(kwargs.get("model_path", self._current_config["repo_id"]))
        return self.load_model(model_path, **kwargs)


# 全局引擎管理器
@dataclass(frozen=True)
class EngineLoadSnapshot:
    """Arguments required to reproduce one successful engine load."""

    model_path: str
    options: dict[str, Any]


class EngineManager:
    """Thread-safe engine manager with transactional model switching."""

    _instance: ClassVar["EngineManager | None"] = None
    _initialized: bool

    def __new__(cls):
        """Singleton pattern retained for backward compatibility."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._engines: dict[str, BaseEngine] = {}
        self._active_engine: BaseEngine | None = None
        self._load_snapshots: dict[str, EngineLoadSnapshot] = {}
        self._manager_lock = threading.RLock()

    def register_engine(self, engine: BaseEngine):
        """Register an engine without changing the active model."""
        with self._manager_lock:
            self._engines[engine.model_id] = engine
        logger.info("Registered engine: %s (%s)", engine.engine_name, engine.model_id)

    def get_engine(self, model_id: str) -> BaseEngine | None:
        with self._manager_lock:
            return self._engines.get(model_id)

    def get_active_engine(self) -> BaseEngine | None:
        with self._manager_lock:
            return self._active_engine

    def set_active_engine(self, model_id: str) -> bool:
        """Activate only a fully loaded registered engine."""
        with self._manager_lock:
            engine = self._engines.get(model_id)
            if engine is None or not engine.is_loaded():
                return False
            current = self._active_engine
            if current and current is not engine:
                if current.status is EngineStatus.GENERATING:
                    logger.error("Cannot switch active engine while generation is running")
                    return False
                current.unload_model()
            self._active_engine = engine
        logger.info("Active engine changed: %s", model_id)
        return True

    @staticmethod
    def _snapshot(model_path: str, options: dict[str, Any]) -> EngineLoadSnapshot:
        return EngineLoadSnapshot(model_path=str(model_path), options=dict(options))

    @staticmethod
    def _load_from_snapshot(engine: BaseEngine, snapshot: EngineLoadSnapshot) -> bool:
        return engine.load_model(snapshot.model_path, **dict(snapshot.options))

    def load_model(self, model_id: str, model_path: str, **kwargs) -> bool:
        """Load or switch models transactionally, restoring the previous model on failure."""
        requested = self._snapshot(model_path, kwargs)
        with self._manager_lock:
            previous = self._active_engine
            if previous and previous.status is EngineStatus.GENERATING:
                logger.error("Cannot load or switch models while generation is running")
                return False

            target = self._engines.get(model_id)
            target_snapshot = self._load_snapshots.get(model_id)
            if target and target.is_loaded() and target_snapshot == requested:
                if previous and previous is not target:
                    previous.unload_model()
                self._active_engine = target
                logger.info("Reused loaded model: %s", model_id)
                return True

            # Legacy callers may activate an engine without a reproducible snapshot.
            # Reuse it instead of risking an irreversible reload.
            if target is previous and target and target.is_loaded() and target_snapshot is None:
                logger.warning("Active model has no load snapshot; keeping it loaded")
                return True

            previous_snapshot = (
                self._load_snapshots.get(previous.model_id)
                if previous and previous.is_loaded()
                else None
            )
            if (
                previous
                and previous is not target
                and previous.is_loaded()
                and not previous_snapshot
            ):
                logger.error("Current model has no load snapshot; safe switching is unavailable")
                return False

            created = target is None
            if target is None:
                target = WanEngine(model_id)
                self._engines[model_id] = target
                logger.info("Registered engine: %s (%s)", target.engine_name, model_id)

            if previous and previous.is_loaded():
                previous.unload_model()
            if target is not previous and target.is_loaded():
                target.unload_model()
            self._active_engine = None

            if target.load_model(model_path, **kwargs):
                self._load_snapshots[model_id] = requested
                self._active_engine = target
                logger.info("Transactional model switch completed: %s", model_id)
                return True

            logger.error("Target model failed to load; restoring previous model: %s", model_id)
            if target.is_loaded():
                target.unload_model()
            self._load_snapshots.pop(model_id, None)
            if created:
                self._engines.pop(model_id, None)

            if previous and previous_snapshot:
                if self._load_from_snapshot(previous, previous_snapshot):
                    self._load_snapshots[previous.model_id] = previous_snapshot
                    self._active_engine = previous
                    logger.warning("Restored previous model: %s", previous.model_id)
                else:
                    logger.critical("Both target and previous model loads failed")
            return False

    def unload_active(self) -> bool:
        """Unload the active engine and clear manager state consistently."""
        with self._manager_lock:
            engine = self._active_engine
            if engine is None:
                return True
            if engine.status is EngineStatus.GENERATING:
                logger.error("Cannot unload a model while generation is running")
                return False
            engine.unload_model()
            self._active_engine = None
            return True

    def unload_all(self):
        """Unload every non-generating engine and clear stale load snapshots."""
        with self._manager_lock:
            for engine in self._engines.values():
                if engine.status is EngineStatus.GENERATING:
                    logger.warning("Skipping generating engine: %s", engine.model_id)
                    continue
                engine.unload_model()
            if self._active_engine and self._active_engine.status is not EngineStatus.GENERATING:
                self._active_engine = None
            self._load_snapshots = {
                model_id: snapshot
                for model_id, snapshot in self._load_snapshots.items()
                if self._engines[model_id].is_loaded()
            }

    def get_loaded_engines(self) -> list[BaseEngine]:
        with self._manager_lock:
            return [engine for engine in self._engines.values() if engine.is_loaded()]


# 全局引擎管理器实例
_engine_manager = None


def get_engine_manager() -> EngineManager:
    """获取引擎管理器实例"""
    global _engine_manager
    if _engine_manager is None:
        _engine_manager = EngineManager()
    return _engine_manager
