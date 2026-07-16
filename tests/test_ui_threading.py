import os
import threading
import time
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from ui.gpu_status import GPUStatusWidget
from ui.main_window import MainWindow, ModelLoadWorker
from utils.gpu_monitor import GPUInfo
from utils.i18n import t
from utils.model_downloader import DownloadProgress, ModelStatus
from utils.task_queue import TaskStatus


class _FakeBackend:
    def __init__(self):
        self.thread_id = None

    def load_model(self, _model_id, **_options):
        self.thread_id = threading.get_ident()
        time.sleep(0.02)
        return True


class _CachedMonitor:
    def get_cached_gpu_info(self):
        return [
            GPUInfo(
                device_id=0,
                name="Cached GPU",
                total_memory=8192,
                used_memory=2048,
                free_memory=6144,
                temperature=50,
                utilization=25,
                power_usage=40.0,
            )
        ]

    def get_all_gpu_info(self):
        raise AssertionError("UI must not execute synchronous GPU queries")


class UIThreadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_model_loading_runs_outside_gui_thread(self):
        backend = _FakeBackend()
        main_thread_id = threading.get_ident()
        results = []
        loop = QEventLoop()
        worker = ModelLoadWorker(backend, "model", {}, None)
        worker.completed.connect(lambda ok, message: (results.append((ok, message)), loop.quit()))
        QTimer.singleShot(2000, loop.quit)
        worker.start()
        loop.exec()
        worker.wait()

        self.assertEqual(results, [(True, "")])
        self.assertNotEqual(backend.thread_id, main_thread_id)

    def test_gpu_widget_reads_cached_data_only(self):
        with patch("ui.gpu_status.get_gpu_monitor", return_value=_CachedMonitor()):
            widget = GPUStatusWidget()
            widget._update_timer.stop()
            widget._update_gpu_status()
            self.assertEqual(widget._name_label.text(), "GPU: Cached GPU")
            widget.deleteLater()

    def test_performance_profile_controls_and_load_options(self):
        captured = {}

        class _Signal:
            def connect(self, callback):
                captured["callback"] = callback

        class _Worker:
            def __init__(self, _backend, model_id, options, _parent):
                captured["model_id"] = model_id
                captured["options"] = options
                self.completed = _Signal()

            def isRunning(self):
                return False

            def start(self):
                captured["started"] = True

        window = MainWindow()
        window._task_timer.stop()
        window._gpu_widget._update_timer.stop()

        balanced_index = window._profile_combo.findData("balanced")
        window._profile_combo.setCurrentIndex(balanced_index)
        self.assertFalse(window._cpu_offload_cb.isEnabled())
        self.assertFalse(window._vae_tiling_cb.isEnabled())
        self.assertFalse(window._flash_attn_cb.isEnabled())

        custom_index = window._profile_combo.findData("custom")
        window._profile_combo.setCurrentIndex(custom_index)
        self.assertTrue(window._cpu_offload_cb.isEnabled())
        self.assertTrue(window._vae_tiling_cb.isEnabled())
        self.assertTrue(window._flash_attn_cb.isEnabled())
        self.assertTrue(window._profile_summary_label.text())

        with patch("ui.main_window.ModelLoadWorker", _Worker):
            window._load_model()

        self.assertTrue(captured["started"])
        self.assertEqual(captured["options"]["performance_profile"], "custom")
        self.assertEqual(captured["options"]["scheduler"], "unipc")
        self.assertEqual(captured["options"]["lora_id"], "")
        self.assertEqual(captured["options"]["lora_scale"], 1.0)
        self.assertIn("cpu_offload", captured["options"])
        self.assertIn("vae_tiling", captured["options"])
        self.assertIn("flash_attention", captured["options"])
        window._model_load_worker = None
        window.deleteLater()

    def test_download_progress_is_polled_and_terminal_state_reenables_actions(self):
        class _DownloadBackend:
            def __init__(self, model_id, progress):
                self._model_id = model_id
                self._progress = progress
                self.cancelled_models = []

            def get_model_download_progress(self, model_id):
                self.assert_model(model_id)
                return self._progress.snapshot()

            def cancel_model_download(self, model_id):
                self.assert_model(model_id)
                self.cancelled_models.append(model_id)
                self._progress.set_state("cancelling")
                return True

            def get_available_models(self):
                return {
                    self._model_id: SimpleNamespace(
                        model_type="t2v",
                        vram_required=8,
                        implemented=True,
                    )
                }

            def get_model_status(self, model_id):
                self.assert_model(model_id)
                return ModelStatus.NOT_DOWNLOADED

            def assert_model(self, model_id):
                if model_id != self._model_id:
                    raise AssertionError(f"Unexpected model ID: {model_id}")

        window = MainWindow()
        window._task_timer.stop()
        window._gpu_widget._update_timer.stop()
        model_id = window._model_combo.currentData()
        self.assertTrue(model_id)

        total_size = 2 * 1024**3
        progress = DownloadProgress(model_id, total_size)
        progress.start_time = datetime.now() - timedelta(seconds=10)
        progress.update_downloaded_size(total_size // 2)
        progress.set_state("downloading")
        backend = _DownloadBackend(model_id, progress)
        window._backend = backend

        window._update_model_download_status()
        self.assertFalse(window._model_download_progress.isHidden())
        self.assertEqual(window._model_download_progress.value(), 50)
        self.assertIn("50.0%", window._model_download_label.text())
        self.assertFalse(window._download_btn.isEnabled())
        self.assertTrue(window._cancel_download_btn.isEnabled())

        window._cancel_model_download()
        self.assertEqual(backend.cancelled_models, [model_id])
        self.assertFalse(window._cancel_download_btn.isEnabled())

        progress.set_state("failed", error="network unavailable", completed=True)
        window._update_model_download_status()
        self.assertTrue(window._download_btn.isEnabled())
        self.assertFalse(window._cancel_download_btn.isEnabled())
        self.assertIn("network unavailable", window._model_download_label.text())
        window.deleteLater()

    def test_generation_prompt_panel_preserves_legacy_control_aliases(self):
        window = MainWindow()
        window._task_timer.stop()
        window._gpu_widget._update_timer.stop()

        panel = window._generation_prompt_panel
        self.assertIs(window._prompt_edit, panel.prompt_edit)
        self.assertIs(window._neg_prompt_edit, panel.negative_prompt_edit)
        self.assertIs(window._history_combo, panel.history_combo)
        self.assertIs(window._generate_btn, panel.generate_button)
        self.assertIs(window._stop_btn, panel.stop_button)
        self.assertIs(window._progress_bar, panel.progress_bar)

        window._prompt_edit.setPlainText("Keep this user-authored prompt")
        panel.set_history_prompts(
            [{"prompt": "A short history prompt"}, {"prompt": "A" * 50}]
        )

        self.assertEqual(window._history_combo.count(), 3)
        self.assertEqual(window._history_combo.itemData(1), "A short history prompt")
        self.assertEqual(window._history_combo.itemText(2), "A" * 40 + "...")
        self.assertEqual(window._prompt_edit.toPlainText(), "Keep this user-authored prompt")
        window.deleteLater()

    def test_generation_uses_one_timer_and_waits_for_cancel_terminal_state(self):
        class _GenerationBackend:
            def __init__(self):
                self.submit_calls = 0
                self.cancelled_task_ids = []
                self.status = {"status": "running", "progress": 15.0}

            def submit_task(self, **_kwargs):
                self.submit_calls += 1
                return "task-1"

            def cancel_task(self, task_id):
                self.cancelled_task_ids.append(task_id)
                self.status = {"status": "cancelled", "progress": 15.0}
                return True

            def get_task_status(self, task_id):
                if task_id != "task-1":
                    raise AssertionError(f"Unexpected task ID: {task_id}")
                return self.status

        window = MainWindow()
        window._task_timer.stop()
        window._gpu_widget._update_timer.stop()
        backend = _GenerationBackend()
        window._backend = backend
        window._prompt_edit.setPlainText("A cinematic sunset over the ocean")

        progress_timer = window._progress_timer
        self.assertIs(progress_timer.parent(), window)
        window._generate()
        window._generate()

        self.assertEqual(backend.submit_calls, 1)
        self.assertIs(window._progress_timer, progress_timer)
        self.assertEqual(window._current_task_id, "task-1")
        self.assertTrue(window._progress_timer.isActive())

        window._stop_generation()
        self.assertEqual(backend.cancelled_task_ids, ["task-1"])
        self.assertFalse(window._progress_timer.isActive())
        self.assertTrue(window._generation_reset_timer.isActive())
        self.assertFalse(window._generate_btn.isEnabled())
        self.assertFalse(window._stop_btn.isEnabled())

        window._on_generation_reset_timeout()
        self.assertIsNone(window._current_task_id)
        self.assertTrue(window._generate_btn.isEnabled())
        self.assertFalse(window._stop_btn.isEnabled())
        window.deleteLater()

    def test_stale_generation_reset_cannot_reset_a_new_session(self):
        window = MainWindow()
        window._task_timer.stop()
        window._gpu_widget._update_timer.stop()
        window._generation_session = 2
        window._pending_reset_session = 1
        window._current_task_id = "task-2"
        window._generate_btn.setEnabled(False)

        window._on_generation_reset_timeout()

        self.assertEqual(window._current_task_id, "task-2")
        self.assertFalse(window._generate_btn.isEnabled())
        window.deleteLater()

    def test_task_panel_refreshes_when_task_state_changes_without_count_change(self):
        task = SimpleNamespace(
            task_id="task-1",
            prompt="A cinematic sunset over the ocean",
            progress=12.6,
            status=TaskStatus.RUNNING,
        )

        class _Queue:
            def get_queue_status(self):
                return {"pending": 0, "running": 1, "completed": 0}

            def get_all_tasks(self):
                return [task]

        class _TaskBackend:
            def get_model_download_progress(self, _model_id):
                return None

            def get_task_queue(self):
                return _Queue()

        window = MainWindow()
        window._task_timer.stop()
        window._gpu_widget._update_timer.stop()
        window._backend = _TaskBackend()

        window._update_tasks()
        self.assertEqual(window._task_list.count(), 1)
        self.assertIn("[13%]", window._task_list.item(0).text())
        self.assertIn(t("running"), window._task_list.item(0).text())

        task.status = TaskStatus.COMPLETED
        task.progress = 100.0
        window._update_tasks()

        self.assertEqual(window._task_list.count(), 1)
        self.assertNotIn("%]", window._task_list.item(0).text())
        self.assertIn(t("completed"), window._task_list.item(0).text())
        window.deleteLater()

    def test_main_window_lifecycle_from_foreign_working_directory(self):
        import tempfile
        from pathlib import Path

        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                window = MainWindow()
                window.show()
                loop = QEventLoop()
                QTimer.singleShot(100, loop.quit)
                loop.exec()
                self.assertEqual(window.windowTitle(), t("app_title"))
                window._backend.shutdown()
                window.deleteLater()
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
