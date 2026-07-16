"""Manifest-gated plugin discovery, activation, and lifecycle management."""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

from plugins.base_plugin import (
    BaseControlNetPlugin,
    BaseEditorPlugin,
    BaseEnginePlugin,
    BaseLoRAPlugin,
    BasePlugin,
)
from plugins.plugin_manifest import PluginManifest, PluginManifestError
from utils.logger import get_logger
from utils.paths import APP_PATHS, resolve_project_path

logger = get_logger("plugin")


@dataclass(frozen=True)
class PluginStatus:
    """Non-executable discovery and runtime status for one plugin."""

    manifest: PluginManifest
    enabled: bool = False
    loaded: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.manifest.to_dict(),
            "enabled": self.enabled,
            "loaded": self.loaded,
            "error": self.error,
        }


class PluginManager:
    """Discover manifests safely and execute code only after explicit enablement."""

    _instance: ClassVar[PluginManager | None] = None
    _initialized: bool

    def __new__(cls, plugins_dir: str = "./plugins", state_path: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, plugins_dir: str = "./plugins", state_path: str | None = None):
        if self._initialized:
            return
        self._initialized = True
        self._plugins_dir = resolve_project_path(plugins_dir)
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = (
            resolve_project_path(state_path)
            if state_path
            else APP_PATHS.configs / "plugins_state.json"
        )
        self._lock = threading.RLock()
        self._manifests: dict[str, PluginManifest] = {}
        self._status_errors: dict[str, str] = {}
        self._plugins: dict[str, BasePlugin] = {}
        self._modules: dict[str, ModuleType] = {}
        self._engine_plugins: dict[str, BaseEnginePlugin] = {}
        self._lora_plugins: dict[str, BaseLoRAPlugin] = {}
        self._controlnet_plugins: dict[str, BaseControlNetPlugin] = {}
        self._editor_plugins: dict[str, BaseEditorPlugin] = {}
        self._enabled_ids = self._load_enabled_ids()
        self.discover_plugins()
        self._activate_persisted_plugins()

    def _load_enabled_ids(self) -> set[str]:
        if not self._state_path.exists():
            return set()
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            enabled = data.get("enabled", []) if isinstance(data, dict) else []
            if not isinstance(enabled, list):
                raise ValueError("enabled must be an array")
            return {str(item) for item in enabled}
        except (OSError, ValueError, json.JSONDecodeError):
            logger.exception("Invalid plugin state; starting with all plugins disabled")
            return set()

    def _save_enabled_ids(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._state_path.with_name(f"{self._state_path.name}.tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump({"enabled": sorted(self._enabled_ids)}, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, self._state_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def _manifest_files(self) -> list[Path]:
        """Return only declarative manifests; never inspect arbitrary Python files."""
        files = list(self._plugins_dir.glob("*.plugin.json"))
        files.extend(self._plugins_dir.glob("*/plugin.json"))
        return sorted(
            {path.resolve() for path in files if path.is_file() and not path.is_symlink()}
        )

    def discover_plugins(self) -> dict[str, PluginManifest]:
        """Parse manifests without importing or executing plugin modules."""
        manifests: dict[str, PluginManifest] = {}
        errors: dict[str, str] = {}
        for manifest_path in self._manifest_files():
            try:
                manifest = PluginManifest.from_file(manifest_path)
                manifest.resolve_entrypoint(self._plugins_dir)
                if manifest.plugin_id in manifests:
                    raise PluginManifestError(f"duplicate plugin id: {manifest.plugin_id}")
                manifests[manifest.plugin_id] = manifest
            except PluginManifestError as error:
                errors[str(manifest_path)] = str(error)
                logger.warning("Ignoring invalid plugin manifest %s: %s", manifest_path, error)

        with self._lock:
            self._manifests = manifests
            self._status_errors = errors
        logger.info("Discovered %s plugin manifests", len(manifests))
        return dict(manifests)

    def _activate_persisted_plugins(self) -> None:
        for plugin_id in sorted(self._enabled_ids):
            if plugin_id not in self._manifests:
                logger.warning("Enabled plugin is no longer installed: %s", plugin_id)
                continue
            if not self._enable_plugin(plugin_id, persist=False):
                logger.error("Persisted plugin failed to activate: %s", plugin_id)

    def _check_dependencies(self, manifest: PluginManifest) -> None:
        missing = [
            dependency
            for dependency in manifest.dependencies
            if importlib.util.find_spec(dependency) is None
        ]
        if missing:
            raise RuntimeError(f"missing plugin dependencies: {', '.join(missing)}")

    def _load_plugin_class(self, manifest: PluginManifest) -> tuple[ModuleType, type[BasePlugin]]:
        module_path, class_name = manifest.resolve_entrypoint(self._plugins_dir)
        module_name = f"videogenai_plugin_{manifest.plugin_id}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to create module spec for {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugin_class = getattr(module, class_name, None)
        if not inspect.isclass(plugin_class) or not issubclass(plugin_class, BasePlugin):
            raise TypeError(f"entrypoint class must subclass BasePlugin: {class_name}")
        if inspect.isabstract(plugin_class):
            raise TypeError(f"entrypoint class is abstract: {class_name}")
        if plugin_class.__module__ != module.__name__:
            raise TypeError("entrypoint must be defined by the declared module")
        return module, plugin_class

    @staticmethod
    def _validate_runtime_info(manifest: PluginManifest, plugin: BasePlugin) -> None:
        info = plugin.info
        if info.name != manifest.plugin_id:
            raise ValueError(
                f"runtime plugin name {info.name!r} must equal manifest id {manifest.plugin_id!r}"
            )
        if info.version != manifest.version:
            raise ValueError("runtime plugin version does not match manifest version")
        if info.plugin_type != manifest.plugin_type:
            raise ValueError("runtime plugin type does not match manifest type")

    def _classify_plugin(self, plugin_id: str, plugin: BasePlugin) -> None:
        if isinstance(plugin, BaseEnginePlugin):
            self._engine_plugins[plugin_id] = plugin
        if isinstance(plugin, BaseLoRAPlugin):
            self._lora_plugins[plugin_id] = plugin
        if isinstance(plugin, BaseControlNetPlugin):
            self._controlnet_plugins[plugin_id] = plugin
        if isinstance(plugin, BaseEditorPlugin):
            self._editor_plugins[plugin_id] = plugin

    def _remove_classification(self, plugin_id: str) -> None:
        self._engine_plugins.pop(plugin_id, None)
        self._lora_plugins.pop(plugin_id, None)
        self._controlnet_plugins.pop(plugin_id, None)
        self._editor_plugins.pop(plugin_id, None)

    def _enable_plugin(self, plugin_id: str, *, persist: bool) -> bool:
        with self._lock:
            if plugin_id in self._plugins:
                return True
            manifest = self._manifests.get(plugin_id)
            if manifest is None:
                self._status_errors[plugin_id] = "plugin manifest was not found"
                return False
            try:
                if not manifest.is_api_compatible:
                    raise RuntimeError(
                        f"incompatible plugin API {manifest.api_version}; host API is 1.0"
                    )
                self._check_dependencies(manifest)
                module, plugin_class = self._load_plugin_class(manifest)
                plugin = plugin_class()
                self._validate_runtime_info(manifest, plugin)
                if not plugin.initialize():
                    raise RuntimeError("plugin initialize() returned False")
                plugin.enable()
                self._plugins[plugin_id] = plugin
                self._modules[plugin_id] = module
                self._classify_plugin(plugin_id, plugin)
                self._status_errors.pop(plugin_id, None)
                self._enabled_ids.add(plugin_id)
                if persist:
                    self._save_enabled_ids()
                logger.info("Enabled plugin: %s v%s", plugin_id, manifest.version)
                return True
            except Exception as error:
                self._status_errors[plugin_id] = str(error)
                logger.exception("Failed to enable plugin: %s", plugin_id)
                return False

    def enable_plugin(self, name: str) -> bool:
        """Explicitly import, initialize, and persist one discovered plugin."""
        return self._enable_plugin(name, persist=True)

    def disable_plugin(self, name: str) -> bool:
        """Cleanup, unload, and persist the disabled state."""
        with self._lock:
            plugin = self._plugins.pop(name, None)
            if plugin is not None:
                try:
                    plugin.cleanup()
                except Exception:
                    logger.exception("Plugin cleanup failed: %s", name)
                plugin.disable()
            self._modules.pop(name, None)
            self._remove_classification(name)
            was_enabled = name in self._enabled_ids
            self._enabled_ids.discard(name)
            self._save_enabled_ids()
            return plugin is not None or was_enabled or name in self._manifests

    def reload_plugins(self) -> None:
        """Cleanup loaded plugins, rediscover manifests, and restore enabled IDs."""
        enabled = set(self._enabled_ids)
        for plugin_id in list(self._plugins):
            self.disable_plugin(plugin_id)
        self._enabled_ids = enabled
        self.discover_plugins()
        self._activate_persisted_plugins()
        self._save_enabled_ids()

    def shutdown(self) -> None:
        """Cleanup active plugins without changing persisted enablement."""
        with self._lock:
            for plugin_id, plugin in list(self._plugins.items()):
                try:
                    plugin.cleanup()
                except Exception:
                    logger.exception("Plugin cleanup failed during shutdown: %s", plugin_id)
                plugin.disable()
            self._plugins.clear()
            self._modules.clear()
            self._engine_plugins.clear()
            self._lora_plugins.clear()
            self._controlnet_plugins.clear()
            self._editor_plugins.clear()

    def get_plugin(self, name: str) -> BasePlugin | None:
        with self._lock:
            return self._plugins.get(name)

    def get_all_plugins(self) -> dict[str, BasePlugin]:
        with self._lock:
            return dict(self._plugins)

    def get_engine_plugins(self) -> dict[str, BaseEnginePlugin]:
        with self._lock:
            return dict(self._engine_plugins)

    def get_lora_plugins(self) -> dict[str, BaseLoRAPlugin]:
        with self._lock:
            return dict(self._lora_plugins)

    def get_controlnet_plugins(self) -> dict[str, BaseControlNetPlugin]:
        with self._lock:
            return dict(self._controlnet_plugins)

    def get_editor_plugins(self) -> dict[str, BaseEditorPlugin]:
        with self._lock:
            return dict(self._editor_plugins)

    def get_plugins_info(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                PluginStatus(
                    manifest=manifest,
                    enabled=plugin_id in self._enabled_ids,
                    loaded=plugin_id in self._plugins,
                    error=self._status_errors.get(plugin_id),
                ).to_dict()
                for plugin_id, manifest in sorted(self._manifests.items())
            ]

    def get_discovery_errors(self) -> dict[str, str]:
        with self._lock:
            return {
                key: value
                for key, value in self._status_errors.items()
                if key not in self._manifests
            }


_plugin_manager: PluginManager | None = None


def get_plugin_manager(
    plugins_dir: str = "./plugins",
    state_path: str | None = None,
) -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(plugins_dir, state_path)
    return _plugin_manager
