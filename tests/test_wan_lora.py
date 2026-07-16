from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from engines.base_engine import EngineStatus
from engines.wan_engine import WanEngine


class FakeLoraPipeline:
    def __init__(self):
        self.loaded = []
        self.adapters = []
        self.unload_calls = 0

    def load_lora_weights(self, path, adapter_name):
        self.loaded.append((path, adapter_name))

    def set_adapters(self, adapter_name, adapter_weights):
        self.adapters.append((adapter_name, adapter_weights))

    def unload_lora_weights(self):
        self.unload_calls += 1


def test_apply_and_unload_lora_use_diffusers_adapter_api(tmp_path: Path):
    engine = WanEngine()
    engine._pipe = FakeLoraPipeline()
    lora_path = tmp_path / "style.safetensors"

    engine._apply_lora(
        lora_id="style",
        lora_path=str(lora_path),
        adapter_name="videogenai_style",
        scale=0.75,
    )

    assert engine._pipe.loaded == [(str(lora_path), "videogenai_style")]
    assert engine._pipe.adapters == [("videogenai_style", 0.75)]
    assert engine._active_lora_id == "style"
    assert engine._active_lora_scale == 0.75

    engine.set_status(EngineStatus.READY)
    assert engine.unload_lora()
    assert engine._pipe.unload_calls == 1
    assert engine._active_lora_id is None


def test_unload_lora_is_rejected_during_generation():
    engine = WanEngine()
    engine._pipe = FakeLoraPipeline()
    engine._active_lora_id = "style"
    engine.set_status(EngineStatus.GENERATING)

    assert not engine.unload_lora()
    assert engine._pipe.unload_calls == 0


def test_lora_requires_supported_pipeline_and_valid_scale(monkeypatch):
    engine = WanEngine()
    engine._pipe = SimpleNamespace()

    with pytest.raises(ValueError, match="greater than 0"):
        engine._apply_lora(lora_id="x", lora_path="x", adapter_name="x", scale=0)
    with pytest.raises(RuntimeError, match="does not support LoRA"):
        engine._apply_lora(lora_id="x", lora_path="x", adapter_name="x", scale=1.0)


def test_missing_peft_has_clear_error(monkeypatch):
    engine = WanEngine()
    engine._pipe = FakeLoraPipeline()
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "peft":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        with pytest.raises(RuntimeError, match="requires the PEFT package"):
            engine._apply_lora(
                lora_id="x",
                lora_path="x.safetensors",
                adapter_name="x",
                scale=1.0,
            )
