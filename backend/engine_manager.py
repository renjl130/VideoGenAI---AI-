"""
后端引擎管理器 - 整合所有后端功能
"""

import os
from typing import Any, ClassVar

from engines.base_engine import GenerationParams
from engines.wan_engine import EngineManager, get_engine_manager
from plugins.plugin_manager import PluginManager, get_plugin_manager
from utils.config_manager import ConfigManager, get_config
from utils.generation_validation import (
    GenerationRequestValues,
    validate_generation_request,
)
from utils.gpu_monitor import GPUInfo, get_gpu_monitor
from utils.history_manager import HistoryManager, HistoryRecord, get_history_manager
from utils.inference_errors import InferenceErrorReport, InferenceRuntimeError
from utils.logger import get_logger
from utils.lora_manager import LoraInfo, LoraManager, get_lora_manager
from utils.model_downloader import (
    DownloadProgress,
    ModelDownloader,
    ModelInfo,
    ModelStatus,
    get_model_downloader,
)
from utils.optimization import (
    PerformanceProfile,
    build_optimization_plan,
    detect_hardware_capabilities,
)
from utils.output_naming import DEFAULT_FILENAME_PATTERN, validate_filename_pattern
from utils.scheduler_registry import SchedulerType
from utils.task_queue import GenerationTask, TaskQueue, TaskType, get_task_queue

logger = get_logger("backend")


class BackendManager:
    """后端管理器 - 协调所有后端功能"""

    _instance: ClassVar["BackendManager | None"] = None
    _initialized: bool

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化后端管理器"""
        if self._initialized:
            return

        self._initialized = True

        # 初始化各个管理器
        self._config = get_config()
        self._gpu_monitor = get_gpu_monitor()
        models_dir = self._config.resolve_path("models.models_dir", "./models")
        output_dir = self._config.resolve_path("output.output_dir", "./outputs")
        self._model_downloader = get_model_downloader(str(models_dir))
        if not self._model_downloader.set_mirror(self._config.models.mirror):
            logger.warning(
                "配置的模型镜像不可用，已保留默认镜像: %s",
                self._config.models.mirror,
            )
        self._lora_manager = get_lora_manager(self._config.models.loras_dir)
        self._task_queue = get_task_queue(self._config.queue.max_concurrent)
        self._history_manager = get_history_manager(str(output_dir / "history"))
        self._engine_manager = get_engine_manager()
        self._plugin_manager = get_plugin_manager("./plugins")

        # 设置任务执行函数
        self._task_queue.set_execute_function(self._execute_generation_task)

        # 注册回调
        self._setup_callbacks()

        # 启动GPU监控
        self._gpu_monitor.start_monitoring(interval=2.0)

        logger.info("后端管理器初始化完成")

    def _setup_callbacks(self):
        """设置回调函数"""
        # 任务队列回调
        self._task_queue.on_task_complete(self._on_task_complete)
        self._task_queue.on_task_fail(self._on_task_fail)

        # 下载回调
        self._model_downloader.add_callback(self._on_download_complete)

    def _execute_generation_task(self, task: GenerationTask) -> dict[str, Any]:
        """执行视频生成任务"""
        logger.info(f"开始执行任务: {task.task_id}")

        # 获取引擎
        engine = self._engine_manager.get_active_engine()
        if not engine or not engine.is_loaded():
            raise RuntimeError("当前没有已加载的模型，无法执行任务")
        if engine.model_id != task.model_id:
            raise RuntimeError(
                f"任务模型与当前加载模型不一致: task={task.model_id}, active={engine.model_id}"
            )

        # 构建生成参数
        params = GenerationParams(
            prompt=task.prompt,
            negative_prompt=task.negative_prompt,
            width=task.width,
            height=task.height,
            num_frames=task.num_frames,
            fps=task.fps,
            steps=task.steps,
            cfg_scale=task.cfg_scale,
            seed=task.seed,
            image_path=task.image_path,
            video_path=task.video_path,
            precision=task.precision,
            cpu_offload=task.cpu_offload,
            vae_tiling=task.vae_tiling,
            progress_callback=lambda p, m: self._task_queue.update_progress(task.task_id, p),
            cancellation_callback=task.is_cancel_requested,
            output_dir=str(self._config.resolve_path("output.output_dir", "./outputs")),
            output_filename_pattern=task.output_filename_pattern,
            task_id=task.task_id,
        )

        # 执行生成
        result = engine.generate(params)

        if not result.success:
            if result.error_report:
                raise InferenceRuntimeError(InferenceErrorReport.from_dict(result.error_report))
            raise RuntimeError(result.error_message or "Generation failed")

        return {
            "output_path": result.output_path,
            "duration": result.duration,
            "seed_used": result.seed_used,
        }

    @staticmethod
    def _task_duration(task: GenerationTask) -> float:
        if task.completed_at and task.started_at:
            return (task.completed_at - task.started_at).total_seconds()
        return 0.0

    def _history_record_for_task(self, task: GenerationTask) -> HistoryRecord:
        """Build one backward-compatible history record for success or failure."""
        return HistoryRecord(
            record_id=task.task_id,
            task_type=task.task_type.value,
            model_id=task.model_id,
            prompt=task.prompt,
            negative_prompt=task.negative_prompt,
            parameters=task.to_dict(),
            output_path=task.output_path or "",
            created_at=task.created_at.isoformat(),
            duration=self._task_duration(task),
            file_size=(
                os.path.getsize(task.output_path)
                if task.output_path and os.path.exists(task.output_path)
                else 0
            ),
            status=task.status.value,
            error_kind=task.error_kind,
            error_message=task.error_message,
            error_details=task.error_details,
        )

    def _on_task_complete(self, task: GenerationTask):
        """Persist successful generation history."""
        logger.info("任务完成: %s", task.task_id)
        if self._config.output.auto_save_history:
            self._history_manager.add_record(self._history_record_for_task(task))

    def _on_task_fail(self, task: GenerationTask):
        """Persist failed generation diagnostics for later troubleshooting."""
        logger.error("任务失败: %s, 错误: %s", task.task_id, task.error_message)
        if self._config.output.auto_save_history:
            self._history_manager.add_record(self._history_record_for_task(task))

    def _on_download_complete(self, model_id: str, progress):
        """下载完成回调"""
        if progress.status == "completed":
            logger.info(f"模型下载完成: {model_id}")

    # ========== 公共接口 ==========

    def get_config(self) -> ConfigManager:
        """获取配置管理器"""
        return self._config

    def get_gpu_monitor(self):
        """获取GPU监控器"""
        return self._gpu_monitor

    def get_model_downloader(self) -> ModelDownloader:
        """获取模型下载管理器"""
        return self._model_downloader

    def get_lora_manager(self) -> LoraManager:
        """Return the validated local LoRA registry."""
        return self._lora_manager

    def get_available_loras(self, refresh: bool = False) -> dict[str, LoraInfo]:
        """Return validated LoRAs; optionally rescan the configured directory."""
        if refresh:
            return self._lora_manager.refresh()
        return self._lora_manager.get_available_loras()

    def get_task_queue(self) -> TaskQueue:
        """获取任务队列"""
        return self._task_queue

    def get_history_manager(self) -> HistoryManager:
        """获取历史记录管理器"""
        return self._history_manager

    def get_engine_manager(self) -> EngineManager:
        """获取引擎管理器"""
        return self._engine_manager

    def get_plugin_manager(self) -> PluginManager:
        """Return the manifest-gated plugin lifecycle manager."""
        return self._plugin_manager

    def get_plugins_info(self) -> list[dict[str, Any]]:
        """Return safe discovery/runtime status without importing disabled plugins."""
        return self._plugin_manager.get_plugins_info()

    def enable_plugin(self, plugin_id: str) -> bool:
        """Explicitly trust and enable one discovered plugin."""
        return self._plugin_manager.enable_plugin(plugin_id)

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable and cleanup one plugin."""
        return self._plugin_manager.disable_plugin(plugin_id)

    def get_gpu_info(self) -> list[GPUInfo]:
        """获取GPU信息"""
        return self._gpu_monitor.get_all_gpu_info()

    def get_downloaded_models(self) -> dict[str, ModelInfo]:
        """获取已下载的模型"""
        return self._model_downloader.get_downloaded_models()

    def get_available_models(self) -> dict[str, ModelInfo]:
        """获取可用模型"""
        return self._model_downloader.get_available_models()

    def get_model_status(self, model_id: str) -> ModelStatus:
        """获取本地模型完整性状态。"""
        return self._model_downloader.get_model_status(model_id)

    def download_model(self, model_id: str) -> bool:
        """Start a resumable background model download."""
        return self._model_downloader.download_model(model_id)

    def cancel_model_download(self, model_id: str) -> bool:
        """Request cooperative cancellation for one active model download."""
        return self._model_downloader.cancel_download(model_id)

    def get_model_download_progress(self, model_id: str) -> DownloadProgress | None:
        """Return a detached download-progress snapshot for safe UI polling."""
        return self._model_downloader.get_download_progress(model_id)

    def load_model(self, model_id: str, **kwargs) -> bool:
        """加载模型并应用统一的加载期优化配置。"""
        queue_status = self._task_queue.get_queue_status()
        if queue_status["pending"] or queue_status["running"]:
            raise RuntimeError("Cannot load or switch models while tasks are pending or running")

        model_path = self._model_downloader.get_model_path(model_id)
        if not model_path:
            status = self._model_downloader.get_model_status(model_id)
            if status is ModelStatus.INCOMPLETE:
                logger.error(f"模型下载不完整: {model_id}")
                return False
            if status is ModelStatus.UNSUPPORTED:
                logger.error(f"当前版本尚未实现该模型: {model_id}")
                return False
            if self._config.models.auto_download:
                logger.info(f"模型未找到，开始下载: {model_id}")
                return self.download_model(model_id) and False
            logger.error(f"模型未下载: {model_id}")
            return False

        optimization = self._config.optimization
        requested_lora_id = str(kwargs.pop("lora_id", "") or "")
        requested_lora_scale = float(kwargs.pop("lora_scale", 1.0))
        lora_info = None
        if requested_lora_id:
            if not 0.0 < requested_lora_scale <= 2.0:
                raise ValueError("LoRA scale must be greater than 0 and at most 2")
            lora_info = self._lora_manager.resolve(requested_lora_id)
        requested_scheduler = SchedulerType.parse(
            str(kwargs.pop("scheduler", self._config.generation.scheduler))
        )
        requested_profile = kwargs.pop(
            "performance_profile",
            optimization.performance_profile,
        )
        profile = PerformanceProfile.parse(str(requested_profile))
        configured_options = {
            "precision": optimization.precision,
            "cpu_offload": optimization.cpu_offload,
            "sequential_offload": optimization.sequential_offload,
            "vae_tiling": optimization.vae_tiling,
            "vae_slicing": True,
            "attention_slicing": optimization.attention_slicing,
            "flash_attention": optimization.flash_attention,
            "torch_compile": optimization.torch_compile,
            "xformers": optimization.xformers,
        }
        configured_options.update(kwargs)
        capabilities = detect_hardware_capabilities(self._config.gpu.device_id)
        model_info = self._model_downloader.get_model_info(model_id)
        model_vram = float(model_info.vram_required if model_info else 0)
        plan = build_optimization_plan(
            profile,
            capabilities,
            model_vram,
            configured_options,
        )
        for warning in plan.warnings:
            logger.warning("optimization plan: %s", warning)
        load_options = plan.to_engine_options()
        load_options["scheduler"] = requested_scheduler.value
        if lora_info:
            load_options["lora_id"] = lora_info.lora_id
            load_options["lora_path"] = str(lora_info.path)
            load_options["lora_adapter_name"] = lora_info.adapter_name
            load_options["lora_scale"] = requested_lora_scale
        logger.info(
            "optimization profile=%s precision=%s scheduler=%s device=cuda:%s",
            plan.profile.value,
            plan.precision,
            requested_scheduler.value,
            plan.device_id,
        )
        return self._engine_manager.load_model(
            model_id,
            str(model_path),
            **load_options,
        )

    def unload_model(self):
        """Unload through EngineManager so active state remains consistent."""
        queue_status = self._task_queue.get_queue_status()
        if queue_status["pending"] or queue_status["running"]:
            raise RuntimeError("Cannot unload models while tasks are pending or running")
        if not self._engine_manager.unload_active():
            raise RuntimeError("Cannot unload the active model while generation is running")

    def submit_task(
        self, task_type: TaskType, prompt: str, negative_prompt: str = "", **kwargs
    ) -> str:
        """提交生成任务"""
        # 创建任务
        model_id = str(kwargs.get("model_id", self._config.models.default_model))
        width = int(kwargs.get("width", 832))
        height = int(kwargs.get("height", 480))
        num_frames = int(kwargs.get("num_frames", 81))
        fps = int(kwargs.get("fps", 16))
        steps = int(kwargs.get("steps", 50))
        cfg_scale = float(kwargs.get("cfg_scale", 5.0))
        seed = int(kwargs.get("seed", -1))
        image_path = kwargs.get("image_path")
        configured_filename_pattern = getattr(
            self._config.output,
            "filename_pattern",
            DEFAULT_FILENAME_PATTERN,
        )
        output_filename_pattern = str(
            kwargs.get("output_filename_pattern", configured_filename_pattern)
        )
        validate_filename_pattern(output_filename_pattern)
        validate_generation_request(
            GenerationRequestValues(
                prompt=prompt,
                width=width,
                height=height,
                num_frames=num_frames,
                fps=fps,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed,
                task_type=task_type.value,
                image_path=str(image_path) if image_path else None,
            )
        )
        active_engine = self._engine_manager.get_active_engine()
        if not active_engine or not active_engine.is_loaded():
            raise RuntimeError("请先加载所选模型，再提交生成任务")
        if active_engine.model_id != model_id:
            raise RuntimeError(
                f"所选模型与当前加载模型不一致: selected={model_id}, "
                f"active={active_engine.model_id}"
            )

        task = GenerationTask(
            task_type=task_type,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model_id=model_id,
            width=width,
            height=height,
            num_frames=num_frames,
            fps=fps,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed,
            image_path=str(image_path) if image_path else None,
            video_path=kwargs.get("video_path"),
            precision=kwargs.get("precision", "auto"),
            cpu_offload=kwargs.get("cpu_offload", False),
            vae_tiling=kwargs.get("vae_tiling", True),
            output_filename_pattern=output_filename_pattern,
        )

        # 保存Prompt历史
        if self._config.output.auto_save_prompt:
            self._history_manager.add_prompt(prompt, task.model_id, task_type.value)

        # 提交任务
        task_id = self._task_queue.add_task(task)
        logger.info(f"提交任务: {task_id}")

        return task_id

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self._task_queue.cancel_task(task_id)

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """获取任务状态"""
        task = self._task_queue.get_task(task_id)
        if task:
            return task.to_dict()
        return None

    def get_queue_status(self) -> dict[str, int]:
        """获取队列状态"""
        return self._task_queue.get_queue_status()

    def get_history(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """获取历史记录"""
        records = self._history_manager.get_history(limit, offset)
        return [r.to_dict() for r in records]

    def get_prompt_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取Prompt历史"""
        return self._history_manager.get_prompts(limit)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        return self._history_manager.get_statistics()

    def clear_cache(self):
        """清除缓存"""
        self._gpu_monitor.clear_cache()
        self._task_queue.clear_completed()

    def shutdown(self):
        """关闭后端"""
        logger.info("关闭后端管理器...")

        # 停止GPU监控
        # Cleanup explicitly enabled plugins before process teardown.
        self._plugin_manager.shutdown()

        self._gpu_monitor.stop_monitoring()

        # 卸载模型
        self.unload_model()

        logger.info("后端管理器已关闭")


# 全局后端管理器实例
_backend_manager = None


def get_backend_manager() -> BackendManager:
    """获取后端管理器实例"""
    global _backend_manager
    if _backend_manager is None:
        _backend_manager = BackendManager()
    return _backend_manager
