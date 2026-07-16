from unittest.mock import patch

from engines.base_engine import EngineStatus
from engines.wan_engine import EngineManager


class FakeEngine:
    def __init__(self, model_id: str, load_results: list[bool]):
        self.model_id = model_id
        self.engine_name = "Fake"
        self.status = EngineStatus.UNLOADED
        self.load_results = list(load_results)
        self.load_calls: list[tuple[str, dict]] = []
        self.unload_calls = 0

    def is_loaded(self):
        return self.status in {EngineStatus.READY, EngineStatus.GENERATING}

    def load_model(self, model_path: str, **options):
        self.load_calls.append((model_path, dict(options)))
        success = self.load_results.pop(0) if self.load_results else True
        self.status = EngineStatus.READY if success else EngineStatus.ERROR
        return success

    def unload_model(self):
        self.unload_calls += 1
        self.status = EngineStatus.UNLOADED


def make_manager():
    EngineManager._instance = None
    return EngineManager()


def test_same_model_and_options_reuse_loaded_engine_without_reload():
    manager = make_manager()
    engine = FakeEngine("model-a", [True])

    with patch("engines.wan_engine.WanEngine", return_value=engine):
        assert manager.load_model("model-a", "a-path", scheduler="unipc")
        assert manager.load_model("model-a", "a-path", scheduler="unipc")

    assert len(engine.load_calls) == 1
    assert engine.unload_calls == 0
    assert manager.get_active_engine() is engine


def test_successful_switch_unloads_previous_and_activates_target():
    manager = make_manager()
    engines = {
        "model-a": FakeEngine("model-a", [True]),
        "model-b": FakeEngine("model-b", [True]),
    }

    with patch("engines.wan_engine.WanEngine", side_effect=lambda model_id: engines[model_id]):
        assert manager.load_model("model-a", "a-path", scheduler="unipc")
        assert manager.load_model("model-b", "b-path", scheduler="flow_match_euler")

    assert engines["model-a"].unload_calls == 1
    assert not engines["model-a"].is_loaded()
    assert engines["model-b"].is_loaded()
    assert manager.get_active_engine() is engines["model-b"]


def test_failed_switch_restores_previous_model_from_snapshot():
    manager = make_manager()
    engines = {
        "model-a": FakeEngine("model-a", [True, True]),
        "model-b": FakeEngine("model-b", [False]),
    }

    with patch("engines.wan_engine.WanEngine", side_effect=lambda model_id: engines[model_id]):
        assert manager.load_model("model-a", "a-path", scheduler="unipc")
        assert not manager.load_model("model-b", "b-path", scheduler="flow_match_euler")

    assert manager.get_active_engine() is engines["model-a"]
    assert engines["model-a"].is_loaded()
    assert engines["model-a"].load_calls == [
        ("a-path", {"scheduler": "unipc"}),
        ("a-path", {"scheduler": "unipc"}),
    ]
    assert manager.get_engine("model-b") is None


def test_switch_is_rejected_while_active_engine_is_generating():
    manager = make_manager()
    engine = FakeEngine("model-a", [True])

    with patch("engines.wan_engine.WanEngine", return_value=engine) as factory:
        assert manager.load_model("model-a", "a-path")
        engine.status = EngineStatus.GENERATING
        assert not manager.load_model("model-b", "b-path")

    assert factory.call_count == 1
    assert manager.get_active_engine() is engine
    assert manager.get_engine("model-b") is None


def test_unload_active_clears_manager_pointer_and_rejects_generation():
    manager = make_manager()
    engine = FakeEngine("model-a", [True])

    with patch("engines.wan_engine.WanEngine", return_value=engine):
        assert manager.load_model("model-a", "a-path")

    engine.status = EngineStatus.GENERATING
    assert not manager.unload_active()
    assert manager.get_active_engine() is engine

    engine.status = EngineStatus.READY
    assert manager.unload_active()
    assert manager.get_active_engine() is None
    assert engine.status is EngineStatus.UNLOADED
