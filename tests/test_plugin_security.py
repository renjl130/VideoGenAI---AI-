import json
from pathlib import Path

import pytest

import plugins.plugin_manager as plugin_module
from plugins.plugin_manager import PluginManager
from plugins.plugin_manifest import PluginManifest, PluginManifestError


@pytest.fixture(autouse=True)
def reset_plugin_singletons():
    PluginManager._instance = None
    plugin_module._plugin_manager = None
    yield
    manager = PluginManager._instance
    if manager is not None:
        manager.shutdown()
    PluginManager._instance = None
    plugin_module._plugin_manager = None


def reset_manager():
    PluginManager._instance = None


def write_plugin(
    root: Path,
    *,
    plugin_id: str = "safe_plugin",
    api_version: str = "1.0",
    dependencies=None,
    include_manifest: bool = True,
):
    package_dir = root / plugin_id
    package_dir.mkdir(parents=True, exist_ok=True)
    marker = package_dir / "imported.txt"
    initialized = package_dir / "initialized.txt"
    cleaned = package_dir / "cleaned.txt"
    module = package_dir / "plugin.py"
    module_source = (
        "from pathlib import Path\n"
        "from plugins.base_plugin import BasePlugin, PluginInfo\n\n"
        f"Path({str(marker)!r}).write_text('imported', encoding='utf-8')\n\n"
        "class TestPlugin(BasePlugin):\n"
        "    @property\n"
        "    def info(self):\n"
        "        return PluginInfo(\n"
        f"            name={plugin_id!r},\n"
        "            version='1.0.0',\n"
        "            author='Tests',\n"
        "            description='Test plugin',\n"
        "            plugin_type='utility',\n"
        "        )\n\n"
        "    def initialize(self):\n"
        f"        Path({str(initialized)!r}).write_text('initialized', encoding='utf-8')\n"
        "        return True\n\n"
        "    def cleanup(self):\n"
        f"        Path({str(cleaned)!r}).write_text('cleaned', encoding='utf-8')\n"
    )
    module.write_text(module_source, encoding="utf-8")
    if include_manifest:
        (package_dir / "plugin.json").write_text(
            json.dumps(
                {
                    "id": plugin_id,
                    "name": "Safe Plugin",
                    "version": "1.0.0",
                    "api_version": api_version,
                    "entrypoint": "plugin.py:TestPlugin",
                    "plugin_type": "utility",
                    "dependencies": dependencies or [],
                }
            ),
            encoding="utf-8",
        )
    return marker, initialized, cleaned


def make_manager(root: Path) -> PluginManager:
    reset_manager()
    return PluginManager(str(root), str(root / "state.json"))


def test_discovery_does_not_execute_manifest_plugin_code(tmp_path: Path):
    marker, initialized, _cleaned = write_plugin(tmp_path)
    manager = make_manager(tmp_path)

    assert not marker.exists()
    assert not initialized.exists()
    info = manager.get_plugins_info()
    assert len(info) == 1
    assert info[0]["id"] == "safe_plugin"
    assert not info[0]["enabled"]
    assert not info[0]["loaded"]


def test_arbitrary_python_without_manifest_is_never_executed(tmp_path: Path):
    marker = tmp_path / "executed.txt"
    (tmp_path / "malicious.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )

    manager = make_manager(tmp_path)

    assert manager.get_plugins_info() == []
    assert not marker.exists()


def test_explicit_enable_executes_initializes_and_persists(tmp_path: Path):
    marker, initialized, cleaned = write_plugin(tmp_path)
    manager = make_manager(tmp_path)

    assert manager.enable_plugin("safe_plugin")
    assert marker.exists()
    assert initialized.exists()
    assert manager.get_plugin("safe_plugin") is not None
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8")) == {
        "enabled": ["safe_plugin"]
    }

    manager.shutdown()
    assert cleaned.exists()
    assert manager.get_plugin("safe_plugin") is None
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8")) == {
        "enabled": ["safe_plugin"]
    }


def test_disable_cleans_up_and_persists_disabled_state(tmp_path: Path):
    _marker, _initialized, cleaned = write_plugin(tmp_path)
    manager = make_manager(tmp_path)
    assert manager.enable_plugin("safe_plugin")

    assert manager.disable_plugin("safe_plugin")

    assert cleaned.exists()
    assert manager.get_plugin("safe_plugin") is None
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8")) == {"enabled": []}


def test_persisted_enablement_is_restored_on_next_start(tmp_path: Path):
    marker, initialized, _cleaned = write_plugin(tmp_path)
    (tmp_path / "state.json").write_text(
        json.dumps({"enabled": ["safe_plugin"]}),
        encoding="utf-8",
    )

    manager = make_manager(tmp_path)

    assert marker.exists()
    assert initialized.exists()
    assert manager.get_plugin("safe_plugin") is not None
    manager.shutdown()


def test_incompatible_api_and_missing_dependency_do_not_execute_code(tmp_path: Path):
    incompatible_marker, _initialized, _cleaned = write_plugin(
        tmp_path,
        plugin_id="incompatible",
        api_version="2.0",
    )
    missing_marker, _initialized2, _cleaned2 = write_plugin(
        tmp_path,
        plugin_id="missing_dependency",
        dependencies=["definitely_missing_videogenai_dependency"],
    )
    manager = make_manager(tmp_path)

    assert not manager.enable_plugin("incompatible")
    assert not manager.enable_plugin("missing_dependency")
    assert not incompatible_marker.exists()
    assert not missing_marker.exists()
    status = {item["id"]: item for item in manager.get_plugins_info()}
    assert "incompatible plugin API" in status["incompatible"]["error"]
    assert "missing plugin dependencies" in status["missing_dependency"]["error"]


def test_manifest_rejects_path_escape_and_invalid_api_version(tmp_path: Path):
    manifest_path = tmp_path / "plugin.json"
    base = {
        "id": "safe_plugin",
        "name": "Safe Plugin",
        "version": "1.0.0",
        "api_version": "1.0",
        "entrypoint": "../outside.py:Plugin",
        "plugin_type": "utility",
    }
    try:
        PluginManifest.from_dict(base, manifest_path=manifest_path)
    except PluginManifestError as error:
        assert "relative .py file" in str(error)
    else:
        raise AssertionError("path traversal must be rejected")

    invalid_api = dict(base, entrypoint="plugin.py:Plugin", api_version="not-a-version")
    try:
        PluginManifest.from_dict(invalid_api, manifest_path=manifest_path)
    except PluginManifestError as error:
        assert "invalid API version" in str(error)
    else:
        raise AssertionError("invalid API version must be rejected")
