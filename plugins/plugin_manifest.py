"""Validated, non-executable plugin manifest schema."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PLUGIN_API_VERSION = "1.0"
_PLUGIN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_CLASS_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DEPENDENCY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_TYPES = frozenset({"utility", "engine", "lora", "controlnet", "editor"})


class PluginManifestError(ValueError):
    """Raised when a plugin manifest is malformed or unsafe."""


def _major(version: str) -> int:
    try:
        return int(version.split(".", 1)[0])
    except (TypeError, ValueError) as error:
        raise PluginManifestError(f"invalid API version: {version}") from error


@dataclass(frozen=True)
class PluginManifest:
    """Metadata discovered without importing or executing plugin code."""

    plugin_id: str
    name: str
    version: str
    api_version: str
    entrypoint: str
    plugin_type: str
    author: str = ""
    description: str = ""
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    manifest_path: Path = field(default=Path(), compare=False)

    @classmethod
    def from_file(cls, path: Path) -> PluginManifest:
        """Parse strict JSON and validate all security-sensitive fields."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise PluginManifestError(f"unable to read manifest: {error}") from error
        if not isinstance(data, dict):
            raise PluginManifestError("manifest root must be an object")
        return cls.from_dict(data, manifest_path=path.resolve())

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, manifest_path: Path) -> PluginManifest:
        required = {"id", "name", "version", "api_version", "entrypoint", "plugin_type"}
        missing = sorted(required - set(data))
        if missing:
            raise PluginManifestError(f"missing manifest fields: {', '.join(missing)}")

        plugin_id = str(data["id"]).strip()
        if not _PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise PluginManifestError("plugin id must match [a-z][a-z0-9_-]{1,63}")

        name = str(data["name"]).strip()
        version = str(data["version"]).strip()
        api_version = str(data["api_version"]).strip()
        _major(api_version)
        entrypoint = str(data["entrypoint"]).strip()
        plugin_type = str(data["plugin_type"]).strip().lower()
        author = str(data.get("author", "")).strip()
        description = str(data.get("description", "")).strip()
        if not name or len(name) > 100:
            raise PluginManifestError("plugin name must contain 1 to 100 characters")
        if not version or len(version) > 32:
            raise PluginManifestError("plugin version must contain 1 to 32 characters")
        if plugin_type not in _ALLOWED_TYPES:
            allowed_types = ", ".join(sorted(_ALLOWED_TYPES))
            raise PluginManifestError(
                f"unsupported plugin type: {plugin_type}; allowed: {allowed_types}"
            )

        file_part, separator, class_name = entrypoint.partition(":")
        if not separator or not file_part or not _CLASS_NAME_PATTERN.fullmatch(class_name):
            raise PluginManifestError("entrypoint must use relative/path.py:ClassName")
        entry_path = Path(file_part)
        if (
            entry_path.is_absolute()
            or entry_path.suffix.lower() != ".py"
            or ".." in entry_path.parts
        ):
            raise PluginManifestError("entrypoint must reference a relative .py file without '..'")

        raw_dependencies = data.get("dependencies", [])
        if not isinstance(raw_dependencies, list):
            raise PluginManifestError("dependencies must be an array of import-module names")
        dependencies: list[str] = []
        for dependency in raw_dependencies:
            module_name = str(dependency).strip()
            if not _DEPENDENCY_PATTERN.fullmatch(module_name):
                raise PluginManifestError(
                    f"invalid dependency module: {module_name}; use a top-level import name"
                )
            if module_name not in dependencies:
                dependencies.append(module_name)

        return cls(
            plugin_id=plugin_id,
            name=name,
            version=version,
            api_version=api_version,
            entrypoint=entrypoint,
            plugin_type=plugin_type,
            author=author,
            description=description,
            dependencies=tuple(dependencies),
            manifest_path=manifest_path,
        )

    @property
    def is_api_compatible(self) -> bool:
        """Allow additive minor API releases but require the same major version."""
        return _major(self.api_version) == _major(PLUGIN_API_VERSION)

    def resolve_entrypoint(self, plugins_root: Path) -> tuple[Path, str]:
        """Resolve the declared module and prove it remains inside the plugin root."""
        file_part, _, class_name = self.entrypoint.partition(":")
        base = self.manifest_path.parent
        resolved = (base / file_part).resolve()
        try:
            resolved.relative_to(plugins_root.resolve())
        except ValueError as error:
            raise PluginManifestError(
                "entrypoint escapes the configured plugin directory"
            ) from error
        if resolved.is_symlink():
            raise PluginManifestError("symbolic-link plugin entrypoints are not allowed")
        if not resolved.is_file():
            raise PluginManifestError(f"entrypoint file does not exist: {resolved}")
        return resolved, class_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "api_version": self.api_version,
            "entrypoint": self.entrypoint,
            "plugin_type": self.plugin_type,
            "author": self.author,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "compatible": self.is_api_compatible,
            "manifest_path": str(self.manifest_path),
        }
