from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from backend.engine_manager import BackendManager
from engines.base_engine import GenerationResult
from utils.inference_errors import (
    InferenceErrorKind,
    InferenceErrorReport,
    InferenceRuntimeError,
)
from utils.task_queue import GenerationTask, TaskStatus


class FakeEngine:
    model_id = "wan"

    def __init__(self, result):
        self.result = result

    def is_loaded(self):
        return True

    def generate(self, _params):
        return self.result


class FakeEngineManager:
    def __init__(self, engine):
        self.engine = engine

    def get_active_engine(self):
        return self.engine


class FakeQueue:
    def update_progress(self, _task_id, _progress):
        pass


class FakeHistory:
    def __init__(self):
        self.records = []

    def add_record(self, record):
        self.records.append(record)


def make_backend(engine):
    backend = object.__new__(BackendManager)
    backend._engine_manager = FakeEngineManager(engine)
    backend._task_queue = FakeQueue()
    backend._config = SimpleNamespace(
        resolve_path=lambda _key, default: Path(default).resolve(),
        output=SimpleNamespace(auto_save_history=True),
    )
    backend._history_manager = FakeHistory()
    return backend


def test_backend_raises_structured_runtime_error_from_generation_result():
    report = InferenceErrorReport(
        kind=InferenceErrorKind.CUDA_OOM,
        phase="t2v_generation",
        user_message="显存不足",
        technical_message="CUDA out of memory",
        recoverable=True,
    )
    engine = FakeEngine(
        GenerationResult(
            success=False,
            error_message=report.user_message,
            error_report=report.to_dict(),
        )
    )
    backend = make_backend(engine)
    task = GenerationTask(model_id="wan", prompt="prompt")

    try:
        BackendManager._execute_generation_task(backend, task)
    except InferenceRuntimeError as error:
        assert error.report == report
    else:
        raise AssertionError("structured generation failure must be raised")


def test_failed_task_is_saved_to_history_with_error_diagnostics():
    backend = make_backend(FakeEngine(GenerationResult(success=True)))
    task = GenerationTask(model_id="wan", prompt="prompt")
    task.status = TaskStatus.FAILED
    task.started_at = datetime.now() - timedelta(seconds=3)
    task.completed_at = datetime.now()
    task.error_message = "显存不足"
    task.error_kind = InferenceErrorKind.CUDA_OOM.value
    task.error_details = {"kind": "cuda_oom", "memory": {"free_mib": 100}}

    BackendManager._on_task_fail(backend, task)

    assert len(backend._history_manager.records) == 1
    record = backend._history_manager.records[0]
    assert record.status == "failed"
    assert record.error_kind == "cuda_oom"
    assert record.error_message == "显存不足"
    assert record.error_details["memory"]["free_mib"] == 100
    assert record.duration >= 3
