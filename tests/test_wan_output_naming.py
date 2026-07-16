from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from engines.base_engine import EngineStatus, GenerationParams
from engines.wan_engine import WanEngine


class FakePipeline:
    def __call__(self, **_kwargs):
        return SimpleNamespace(frames=[[object()]])


def test_t2v_generation_uses_configured_filename_pattern(tmp_path: Path):
    engine = WanEngine("wan2.1-t2v-1.3b")
    engine._pipe = FakePipeline()
    engine.set_status(EngineStatus.READY)
    params = GenerationParams(
        prompt="A test prompt",
        steps=1,
        seed=123,
        output_dir=str(tmp_path),
        output_filename_pattern="{task}_{model}_{seed}_{task_id}",
        task_id="task-42",
    )

    def fake_export(_frames, output_path, fps):
        assert fps == params.fps
        Path(output_path).write_bytes(b"video")
        return output_path

    with (
        patch("engines.wan_engine.torch.Generator") as generator,
        patch("diffusers.utils.export_to_video", side_effect=fake_export),
    ):
        generator.return_value.manual_seed.return_value = object()
        result = engine.generate_t2v(params)

    assert result.success
    assert result.output_path is not None
    output_path = Path(result.output_path)
    assert output_path.name == "t2v_wan2.1-t2v-1.3b_123_task-42.mp4"
    assert output_path.read_bytes() == b"video"
    assert engine.status is EngineStatus.READY


def test_t2v_failed_export_does_not_leave_empty_output_file(tmp_path: Path):
    engine = WanEngine("wan2.1-t2v-1.3b")
    engine._pipe = FakePipeline()
    engine.set_status(EngineStatus.READY)
    params = GenerationParams(
        prompt="A test prompt",
        steps=1,
        seed=123,
        output_dir=str(tmp_path),
        output_filename_pattern="{task}_{seed}",
    )

    with (
        patch("engines.wan_engine.torch.Generator") as generator,
        patch("diffusers.utils.export_to_video", side_effect=RuntimeError("encoder failed")),
    ):
        generator.return_value.manual_seed.return_value = object()
        result = engine.generate_t2v(params)

    assert not result.success
    assert "encoder failed" in (result.error_message or "")
    assert list(tmp_path.iterdir()) == []
