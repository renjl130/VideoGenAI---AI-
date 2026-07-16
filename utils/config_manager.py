"""统一配置管理器。"""

import copy
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from utils.logger import get_logger
from utils.output_naming import validate_filename_pattern
from utils.paths import APP_PATHS, resolve_project_path
from utils.scheduler_registry import SchedulerType

logger = get_logger("config")
T = TypeVar("T")


class ConfigError(ValueError):
    """配置内容无效。"""


@dataclass
class AppConfig:
    name: str = "VideoGenAI"
    version: str = "1.0.0"
    language: str = "zh_CN"
    theme: str = "dark"


@dataclass
class ModelConfig:
    default_model: str = "wan2.1-t2v-1.3b"
    models_dir: str = "./models"
    loras_dir: str = "./loras"
    cache_dir: str = "./cache"
    auto_download: bool = True
    mirror: str = "huggingface"


@dataclass
class GenerationConfig:
    default_resolution: str = "832x480"
    default_fps: int = 16
    default_frames: int = 81
    default_steps: int = 50
    default_cfg_scale: float = 5.0
    default_seed: int = -1
    negative_prompt: str = ""
    scheduler: str = "unipc"


@dataclass
class OptimizationConfig:
    performance_profile: str = "balanced"
    precision: str = "auto"
    torch_compile: bool = False
    flash_attention: bool = True
    xformers: bool = True
    sage_attention: bool = False
    cpu_offload: bool = False
    sequential_offload: bool = False
    attention_slicing: bool = False
    vae_tiling: bool = True
    low_vram_mode: bool = False
    high_performance_mode: bool = False


@dataclass
class OutputConfig:
    output_dir: str = "./outputs"
    auto_save_history: bool = True
    auto_save_prompt: bool = True
    filename_pattern: str = "{timestamp}_{model}_{seed}"


@dataclass
class GPUConfig:
    device_id: int = 0
    memory_fraction: float = 0.9
    auto_manage_memory: bool = True


@dataclass
class QueueConfig:
    max_concurrent: int = 1
    auto_retry: bool = True
    max_retries: int = 3


class ConfigManager:
    """线程安全、可恢复并保持旧公共接口的配置管理器。"""

    _instance: ClassVar["ConfigManager | None"] = None
    _initialized: bool

    def __new__(cls, config_path: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str | None = None):
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.RLock()
        self._config_path = str(
            resolve_project_path(config_path) if config_path else APP_PATHS.configs / "config.json"
        )
        self._default_config_path = APP_PATHS.configs / "default_config.json"
        self._config: dict[str, Any] = {}
        self.load()

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ConfigError(f"配置根节点必须是对象: {path}")
        return data

    @staticmethod
    def _merge_config(base: dict[str, Any], override: dict[str, Any]):
        for key, value in override.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                ConfigManager._merge_config(base[key], value)
            else:
                base[key] = value

    @staticmethod
    def _atomic_write(path: Path, data: dict[str, Any]):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)

    def _backup_invalid_user_config(self, path: Path):
        if not path.exists():
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(f"{path.stem}.invalid_{timestamp}{path.suffix}")
        try:
            os.replace(path, backup)
            logger.error("无效配置已备份到: %s", backup)
        except OSError:
            logger.exception("备份无效配置失败: %s", path)

    @staticmethod
    def _normalize_legacy_optimization(
        merged: dict[str, Any],
        user_config: dict[str, Any] | None,
    ) -> None:
        """Map legacy optimization booleans to the new profile field."""
        optimization = merged.setdefault("optimization", {})
        if not isinstance(optimization, dict):
            raise ConfigError("optimization must be an object")

        user_optimization: dict[str, Any] = {}
        if user_config:
            candidate = user_config.get("optimization", {})
            if isinstance(candidate, dict):
                user_optimization = candidate

        if "performance_profile" in user_optimization:
            return
        if bool(user_optimization.get("low_vram_mode")):
            optimization["performance_profile"] = "low_vram"
        elif bool(user_optimization.get("high_performance_mode")):
            optimization["performance_profile"] = "high_performance"

    @staticmethod
    def _validate(config: dict[str, Any]):
        optimization = config.get("optimization", {})
        profile = str(optimization.get("performance_profile", "balanced"))
        allowed_profiles = {"balanced", "low_vram", "high_performance", "custom"}
        if profile not in allowed_profiles:
            raise ConfigError(
                "optimization.performance_profile must be one of: "
                + ", ".join(sorted(allowed_profiles))
            )

        models = config.get("models", {})
        mirror = str(models.get("mirror", "huggingface"))
        supported_mirrors = {"huggingface", "hf-mirror", "modelscope"}
        if mirror not in supported_mirrors:
            raise ConfigError(
                "models.mirror must be one of: " + ", ".join(sorted(supported_mirrors))
            )

        queue = config.get("queue", {})
        if int(queue.get("max_concurrent", 1)) < 1:
            raise ConfigError("queue.max_concurrent 必须大于等于 1")
        gpu = config.get("gpu", {})
        fraction = float(gpu.get("memory_fraction", 0.9))
        if not 0 < fraction <= 1:
            raise ConfigError("gpu.memory_fraction 必须在 (0, 1] 范围内")
        generation = config.get("generation", {})
        for key in ("default_fps", "default_frames", "default_steps"):
            if int(generation.get(key, 1)) < 1:
                raise ConfigError(f"generation.{key} 必须大于等于 1")
        try:
            SchedulerType.parse(str(generation.get("scheduler", "unipc")))
        except ValueError as error:
            raise ConfigError(f"generation.scheduler is invalid: {error}") from error

        output = config.get("output", {})
        try:
            validate_filename_pattern(
                str(output.get("filename_pattern", "{timestamp}_{model}_{seed}"))
            )
        except ValueError as error:
            raise ConfigError(f"output.filename_pattern is invalid: {error}") from error

    def load(self) -> dict[str, Any]:
        with self._lock:
            if not self._default_config_path.exists():
                raise ConfigError(f"默认配置不存在: {self._default_config_path}")
            default_config = self._read_json(self._default_config_path)
            merged = copy.deepcopy(default_config)
            user_path = Path(self._config_path)
            if user_path.exists():
                try:
                    user_config = self._read_json(user_path)
                    self._merge_config(merged, user_config)
                    self._normalize_legacy_optimization(merged, user_config)
                    self._validate(merged)
                except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                    logger.warning("用户配置无效，将恢复默认配置: %s", error)
                    self._backup_invalid_user_config(user_path)
                    merged = copy.deepcopy(default_config)
                    self._validate(merged)
                    self._config = merged
                    self.save()
                    return copy.deepcopy(self._config)
            else:
                self._normalize_legacy_optimization(merged, None)
                self._validate(merged)
                self._config = merged
                self.save()
                return copy.deepcopy(self._config)

            self._config = merged
            return copy.deepcopy(self._config)

    def save(self):
        with self._lock:
            self._validate(self._config)
            self._atomic_write(Path(self._config_path), self._config)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            value: Any = self._config
            for part in key.split("."):
                if not isinstance(value, dict) or part not in value:
                    return default
                value = value[part]
            return copy.deepcopy(value)

    def set(self, key: str, value: Any):
        with self._lock:
            parts = key.split(".")
            target = self._config
            for part in parts[:-1]:
                child = target.get(part)
                if not isinstance(child, dict):
                    child = {}
                    target[part] = child
                target = child
            target[parts[-1]] = value

    def get_section(self, section: str) -> dict[str, Any]:
        value = self.get(section, {})
        return value if isinstance(value, dict) else {}

    def update_section(self, section: str, data: dict[str, Any]):
        with self._lock:
            current = self._config.setdefault(section, {})
            if not isinstance(current, dict):
                current = {}
                self._config[section] = current
            current.update(copy.deepcopy(data))

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._config)

    def reset(self):
        with self._lock:
            self._config = self._read_json(self._default_config_path)
            self._validate(self._config)
            self.save()

    def resolve_path(self, key: str, default: str) -> Path:
        """读取配置路径并相对项目根目录解析。"""
        return resolve_project_path(self.get(key, default))

    def _section_dataclass(self, section: str, cls: type[T]) -> T:
        data = self.get_section(section)
        dataclass_fields = getattr(cls, "__dataclass_fields__", {})
        allowed = set(dataclass_fields)
        filtered = {key: value for key, value in data.items() if key in allowed}
        unknown = sorted(set(data) - allowed)
        if unknown:
            logger.warning("忽略配置段 %s 的未知字段: %s", section, unknown)
        return cls(**filtered)

    @property
    def app(self) -> AppConfig:
        return self._section_dataclass("app", AppConfig)

    @property
    def models(self) -> ModelConfig:
        return self._section_dataclass("models", ModelConfig)

    @property
    def generation(self) -> GenerationConfig:
        return self._section_dataclass("generation", GenerationConfig)

    @property
    def optimization(self) -> OptimizationConfig:
        return self._section_dataclass("optimization", OptimizationConfig)

    @property
    def output(self) -> OutputConfig:
        return self._section_dataclass("output", OutputConfig)

    @property
    def gpu(self) -> GPUConfig:
        return self._section_dataclass("gpu", GPUConfig)

    @property
    def queue(self) -> QueueConfig:
        return self._section_dataclass("queue", QueueConfig)


_config_manager = None


def get_config(config_path: str | None = None) -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def reload_config(config_path: str | None = None) -> ConfigManager:
    """销毁旧单例并从指定路径重新加载。"""
    global _config_manager
    ConfigManager._instance = None
    _config_manager = ConfigManager(config_path)
    return _config_manager
