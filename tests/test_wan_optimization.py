from types import SimpleNamespace

import pytest

from engines.wan_engine import WanEngine


class _Vae:
    def __init__(self) -> None:
        self.tiling_enabled = False
        self.slicing_enabled = False

    def enable_tiling(self) -> None:
        self.tiling_enabled = True

    def enable_slicing(self) -> None:
        self.slicing_enabled = True


class _OffloadPipeline:
    def __init__(self, *, fail_sequential: bool = False) -> None:
        self.fail_sequential = fail_sequential
        self.sequential_enabled = False
        self.vae = _Vae()
        self.transformer = SimpleNamespace()

    def enable_sequential_cpu_offload(self) -> None:
        if self.fail_sequential:
            raise RuntimeError("accelerate unavailable")
        self.sequential_enabled = True

    def enable_attention_slicing(self) -> None:
        raise RuntimeError("not supported by this pipeline")


def test_requested_sequential_offload_fails_fast_when_unavailable():
    engine = WanEngine()
    engine._pipe = _OffloadPipeline(fail_sequential=True)

    with pytest.raises(RuntimeError, match="Sequential CPU offload was requested"):
        engine._apply_optimizations(
            cpu_offload=False,
            vae_tiling=False,
            kwargs={"sequential_offload": True, "flash_attention": False},
        )


def test_optional_feature_failure_does_not_disable_required_sequential_offload():
    engine = WanEngine()
    pipeline = _OffloadPipeline()
    engine._pipe = pipeline

    engine._apply_optimizations(
        cpu_offload=False,
        vae_tiling=True,
        kwargs={
            "sequential_offload": True,
            "attention_slicing": True,
            "vae_slicing": True,
            "flash_attention": False,
        },
    )

    assert pipeline.sequential_enabled
    assert pipeline.vae.tiling_enabled
    assert pipeline.vae.slicing_enabled
