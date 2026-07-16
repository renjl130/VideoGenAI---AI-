import json
import tempfile
import unittest
from pathlib import Path

import utils.config_manager as config_module
from utils.config_manager import ConfigManager, reload_config
from utils.paths import PROJECT_ROOT


class ConfigManagerTests(unittest.TestCase):
    def tearDown(self):
        ConfigManager._instance = None
        config_module._config_manager = None

    def test_reload_uses_new_path_and_ignores_unknown_typed_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = Path(temp_dir) / "first.json"
            second_path = Path(temp_dir) / "second.json"
            first_path.write_text(
                json.dumps({"app": {"language": "en_US", "future": True}}),
                encoding="utf-8",
            )
            second_path.write_text(
                json.dumps({"app": {"language": "zh_CN"}}),
                encoding="utf-8",
            )
            first = reload_config(str(first_path))
            self.assertEqual(first.app.language, "en_US")
            second = reload_config(str(second_path))
            self.assertEqual(second.app.language, "zh_CN")
            self.assertEqual(Path(second._config_path), second_path.resolve())

    def test_corrupt_user_config_is_backed_up_and_recovered(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text("{broken", encoding="utf-8")
            manager = reload_config(str(config_path))
            self.assertEqual(manager.app.name, "VideoGenAI")
            self.assertTrue(config_path.exists())
            self.assertTrue(list(Path(temp_dir).glob("config.invalid_*.json")))
            self.assertFalse(list(Path(temp_dir).glob("*.tmp")))

    def test_relative_paths_resolve_from_project_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = reload_config(str(Path(temp_dir) / "config.json"))
            self.assertEqual(
                manager.resolve_path("models.models_dir", "./models"),
                (PROJECT_ROOT / "models").resolve(),
            )

    def test_invalid_scheduler_is_backed_up_and_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps({"generation": {"scheduler": "unknown"}}),
                encoding="utf-8",
            )

            manager = reload_config(str(config_path))

            self.assertEqual(manager.generation.scheduler, "unipc")
            self.assertEqual(
                len(list(Path(temp_dir).glob("config.invalid_*.json"))),
                1,
            )

    def test_invalid_output_filename_pattern_is_backed_up_and_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps({"output": {"filename_pattern": "{prompt}"}}),
                encoding="utf-8",
            )

            manager = reload_config(str(config_path))

            self.assertEqual(
                manager.output.filename_pattern,
                "{timestamp}_{model}_{seed}",
            )
            self.assertEqual(
                len(list(Path(temp_dir).glob("config.invalid_*.json"))),
                1,
            )


if __name__ == "__main__":
    unittest.main()
