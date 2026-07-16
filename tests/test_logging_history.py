import json
import logging
import tempfile
import threading
import unittest
from pathlib import Path

from utils.history_manager import HistoryManager, HistoryRecord
from utils.logger import ColoredFormatter


class LoggingTests(unittest.TestCase):
    def test_colored_formatter_does_not_mutate_record(self):
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", (), None)
        original = record.levelname
        ColoredFormatter("%(levelname)s %(message)s").format(record)
        self.assertEqual(record.levelname, original)


class HistoryPersistenceTests(unittest.TestCase):
    def setUp(self):
        HistoryManager._instance = None
        self.temp = tempfile.TemporaryDirectory()
        self.manager = HistoryManager(self.temp.name)

    def tearDown(self):
        HistoryManager._instance = None
        self.temp.cleanup()

    def test_record_does_not_double_count_prompt(self):
        self.manager.add_prompt("prompt", "model", "text_to_video")
        self.manager.add_record(
            HistoryRecord(
                record_id="record",
                task_type="text_to_video",
                model_id="model",
                prompt="prompt",
                negative_prompt="",
                parameters={},
                output_path="output.mp4",
                created_at="2026-07-16T00:00:00",
                duration=1.0,
                file_size=1,
            )
        )
        prompts = self.manager.get_prompts()
        self.assertEqual(prompts[0]["use_count"], 1)
        self.assertFalse(list(Path(self.temp.name).glob("*.tmp")))

    def test_concurrent_prompt_updates_are_serialized(self):
        threads = [
            threading.Thread(target=self.manager.add_prompt, args=("same",)) for _ in range(10)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(self.manager.get_prompts()[0]["use_count"], 10)


if __name__ == "__main__":
    unittest.main()


def test_legacy_history_records_load_with_new_error_fields_defaulted(tmp_path):
    from utils.history_manager import HistoryManager

    history_dir = tmp_path / "history"
    history_dir.mkdir()
    (history_dir / "history.json").write_text(
        json.dumps(
            [
                {
                    "record_id": "legacy",
                    "task_type": "text_to_video",
                    "model_id": "wan",
                    "prompt": "old",
                    "negative_prompt": "",
                    "parameters": {},
                    "output_path": "old.mp4",
                    "created_at": "2026-01-01T00:00:00",
                    "duration": 1.0,
                    "file_size": 10,
                }
            ]
        ),
        encoding="utf-8",
    )
    HistoryManager._instance = None
    manager = HistoryManager(str(history_dir))

    record = manager.get_history()[0]
    assert record.status == "completed"
    assert record.error_kind is None
    assert record.error_details == {}
    HistoryManager._instance = None
