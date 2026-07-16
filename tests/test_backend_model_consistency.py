from types import SimpleNamespace

import pytest

from backend.engine_manager import BackendManager
from utils.task_queue import TaskType


class FakeEngineManager:
    def __init__(self, engine):
        self.engine = engine

    def get_active_engine(self):
        return self.engine


class FakeQueue:
    def add_task(self, _task):
        raise AssertionError("An inconsistent task must never enter the queue")


class FakeHistory:
    def add_prompt(self, *_args):
        raise AssertionError("A rejected task must not update prompt history")


def make_backend(engine):
    backend = object.__new__(BackendManager)
    backend._config = SimpleNamespace(
        models=SimpleNamespace(default_model="selected-model"),
        output=SimpleNamespace(auto_save_prompt=True),
    )
    backend._engine_manager = FakeEngineManager(engine)
    backend._task_queue = FakeQueue()
    backend._history_manager = FakeHistory()
    return backend


def submit_valid_request(backend):
    return BackendManager.submit_task(
        backend,
        TaskType.TEXT_TO_VIDEO,
        "A valid prompt",
        model_id="selected-model",
        width=832,
        height=480,
        num_frames=81,
        fps=16,
        steps=50,
        cfg_scale=5.0,
        seed=-1,
    )


def test_submit_rejects_when_no_model_is_loaded():
    backend = make_backend(None)

    with pytest.raises(RuntimeError) as captured:
        submit_valid_request(backend)

    assert str(captured.value)


def test_submit_rejects_when_selected_model_differs_from_active_engine():
    engine = SimpleNamespace(model_id="other-model", is_loaded=lambda: True)
    backend = make_backend(engine)

    with pytest.raises(RuntimeError) as captured:
        submit_valid_request(backend)

    message = str(captured.value)
    assert "selected-model" in message
    assert "other-model" in message
