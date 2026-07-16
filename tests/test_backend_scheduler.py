from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.engine_manager import BackendManager
from utils.model_downloader import ModelStatus
from utils.optimization import OptimizationPlan, PerformanceProfile


class FakeDownloader:
    def __init__(self, model_path: Path):
        self.model_path = model_path

    def get_model_path(self, _model_id):
        return self.model_path

    def get_model_info(self, _model_id):
        return SimpleNamespace(vram_required=8)

    def get_model_status(self, _model_id):
        return ModelStatus.READY


class FakeLoraManager:
    def resolve(self, lora_id):
        if lora_id != "style":
            raise KeyError(lora_id)
        return SimpleNamespace(
            lora_id="style",
            path=Path("C:/loras/style.safetensors"),
            adapter_name="videogenai_style",
        )


class FakeQueue:
    def get_queue_status(self):
        return {"pending": 0, "running": 0}


class FakeEngineManager:
    def __init__(self):
        self.call = None

    def load_model(self, model_id, model_path, **options):
        self.call = (model_id, model_path, options)
        return True


def test_backend_passes_scheduler_separately_from_optimization_plan(tmp_path: Path):
    backend = object.__new__(BackendManager)
    backend._model_downloader = FakeDownloader(tmp_path)
    backend._engine_manager = FakeEngineManager()
    backend._task_queue = FakeQueue()
    backend._lora_manager = FakeLoraManager()
    backend._config = SimpleNamespace(
        models=SimpleNamespace(auto_download=False),
        generation=SimpleNamespace(scheduler="unipc"),
        optimization=SimpleNamespace(
            performance_profile="balanced",
            precision="auto",
            cpu_offload=False,
            sequential_offload=False,
            vae_tiling=True,
            attention_slicing=False,
            flash_attention=True,
            torch_compile=False,
            xformers=False,
        ),
        gpu=SimpleNamespace(device_id=0),
    )
    plan = OptimizationPlan(
        profile=PerformanceProfile.BALANCED,
        precision="fp16",
        cpu_offload=False,
        sequential_offload=False,
        vae_tiling=True,
        vae_slicing=True,
        attention_slicing=False,
        flash_attention=True,
        xformers=False,
        torch_compile=False,
        device_id=0,
    )

    with (
        patch("backend.engine_manager.detect_hardware_capabilities"),
        patch("backend.engine_manager.build_optimization_plan", return_value=plan) as build,
    ):
        assert BackendManager.load_model(backend, "wan", scheduler="flow_match_euler")

    configured_options = build.call_args.args[3]
    assert "scheduler" not in configured_options
    assert backend._engine_manager.call is not None
    model_id, model_path, engine_options = backend._engine_manager.call
    assert model_id == "wan"
    assert model_path == str(tmp_path)
    assert engine_options["scheduler"] == "flow_match_euler"


def test_backend_resolves_lora_id_and_keeps_it_out_of_optimization_options(tmp_path: Path):
    backend = object.__new__(BackendManager)
    backend._model_downloader = FakeDownloader(tmp_path)
    backend._engine_manager = FakeEngineManager()
    backend._task_queue = FakeQueue()
    backend._lora_manager = FakeLoraManager()
    backend._config = SimpleNamespace(
        models=SimpleNamespace(auto_download=False),
        generation=SimpleNamespace(scheduler="unipc"),
        optimization=SimpleNamespace(
            performance_profile="balanced",
            precision="auto",
            cpu_offload=False,
            sequential_offload=False,
            vae_tiling=True,
            attention_slicing=False,
            flash_attention=True,
            torch_compile=False,
            xformers=False,
        ),
        gpu=SimpleNamespace(device_id=0),
    )
    plan = OptimizationPlan(
        profile=PerformanceProfile.BALANCED,
        precision="fp16",
        cpu_offload=False,
        sequential_offload=False,
        vae_tiling=True,
        vae_slicing=True,
        attention_slicing=False,
        flash_attention=True,
        xformers=False,
        torch_compile=False,
        device_id=0,
    )

    with (
        patch("backend.engine_manager.detect_hardware_capabilities"),
        patch("backend.engine_manager.build_optimization_plan", return_value=plan) as build,
    ):
        assert BackendManager.load_model(backend, "wan", lora_id="style", lora_scale=0.8)

    configured_options = build.call_args.args[3]
    assert "lora_id" not in configured_options
    assert "lora_scale" not in configured_options
    engine_options = backend._engine_manager.call[2]
    assert engine_options["lora_id"] == "style"
    assert engine_options["lora_path"].endswith("style.safetensors")
    assert engine_options["lora_adapter_name"] == "videogenai_style"
    assert engine_options["lora_scale"] == 0.8


def test_backend_rejects_invalid_lora_strength_before_engine_load(tmp_path: Path):
    backend = object.__new__(BackendManager)
    backend._model_downloader = FakeDownloader(tmp_path)
    backend._engine_manager = FakeEngineManager()
    backend._task_queue = FakeQueue()
    backend._lora_manager = FakeLoraManager()
    backend._config = SimpleNamespace(
        models=SimpleNamespace(auto_download=False),
        generation=SimpleNamespace(scheduler="unipc"),
        optimization=SimpleNamespace(performance_profile="balanced"),
    )

    with pytest.raises(ValueError, match="at most 2"):
        BackendManager.load_model(backend, "wan", lora_id="style", lora_scale=3.0)
