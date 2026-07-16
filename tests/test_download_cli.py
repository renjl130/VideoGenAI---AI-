from datetime import datetime, timedelta
from types import SimpleNamespace

from scripts.download_model import _console_output, wait_for_download
from utils.model_downloader import DownloadProgress, ModelStatus


class _FakeBackend:
    def __init__(self, model_id: str, progress: DownloadProgress, status: ModelStatus):
        self.model_id = model_id
        self.progress = progress
        self.status = status
        self.started = False

    def get_available_models(self):
        return {
            self.model_id: SimpleNamespace(
                description="Test model",
                download_size=2.0,
                implemented=True,
            )
        }

    def get_model_status(self, model_id: str) -> ModelStatus:
        assert model_id == self.model_id
        return self.status

    def download_model(self, model_id: str) -> bool:
        assert model_id == self.model_id
        self.started = True
        return True

    def get_model_download_progress(self, model_id: str) -> DownloadProgress:
        assert model_id == self.model_id
        return self.progress.snapshot()


def _progress(model_id: str, status: str) -> DownloadProgress:
    progress = DownloadProgress(model_id, 2 * 1024**3)
    progress.start_time = datetime.now() - timedelta(seconds=10)
    progress.update_downloaded_size(2 * 1024**3)
    progress.set_state(
        status,
        error="network error" if status == "failed" else None,
        completed=True,
    )
    return progress


def test_foreground_download_reports_verified_completion():
    model_id = "test-model"
    backend = _FakeBackend(model_id, _progress(model_id, "completed"), ModelStatus.READY)
    messages: list[str] = []

    result = wait_for_download(backend, model_id, poll_interval=0.1, output=messages.append)

    assert result == 0
    assert not backend.started
    assert any("already complete" in message for message in messages)


def test_foreground_download_does_not_claim_success_for_incomplete_completion():
    model_id = "test-model"
    backend = _FakeBackend(model_id, _progress(model_id, "completed"), ModelStatus.INCOMPLETE)
    messages: list[str] = []

    result = wait_for_download(backend, model_id, poll_interval=0.1, output=messages.append)

    assert result == 1
    assert any("did not report READY" in message for message in messages)


def test_foreground_download_reports_cancelled_as_interrupt_exit_code():
    model_id = "test-model"
    backend = _FakeBackend(model_id, _progress(model_id, "cancelled"), ModelStatus.INCOMPLETE)
    messages: list[str] = []

    result = wait_for_download(backend, model_id, poll_interval=0.1, output=messages.append)

    assert result == 130
    assert any("Partial files were retained" in message for message in messages)

def test_console_output_flushes_redirected_status(monkeypatch):
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_print(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr("builtins.print", fake_print)

    _console_output("downloading: 10.0%")

    assert calls == [(("downloading: 10.0%",), {"flush": True})]

