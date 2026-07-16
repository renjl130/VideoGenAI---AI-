import pytest

from utils.optimization import (
    HardwareCapabilities,
    PerformanceProfile,
    build_optimization_plan,
)


def capable_gpu(total_vram_gib: float = 24.0) -> HardwareCapabilities:
    return HardwareCapabilities(
        cuda_available=True,
        device_count=1,
        device_id=0,
        device_name="Test GPU",
        total_vram_gib=total_vram_gib,
        bf16_supported=True,
        native_sdpa_available=True,
        xformers_available=True,
        torch_compile_available=True,
    )


def test_balanced_profile_prefers_safe_defaults_with_enough_vram():
    plan = build_optimization_plan(PerformanceProfile.BALANCED, capable_gpu(), 8.0)

    assert not plan.cpu_offload
    assert not plan.sequential_offload
    assert plan.vae_tiling
    assert plan.vae_slicing
    assert plan.flash_attention
    assert not plan.xformers
    assert not plan.torch_compile


def test_balanced_profile_selects_sequential_offload_when_vram_is_far_below_requirement():
    plan = build_optimization_plan(PerformanceProfile.BALANCED, capable_gpu(8.0), 16.0)

    assert plan.sequential_offload
    assert not plan.cpu_offload
    assert plan.attention_slicing
    assert any("far below" in warning for warning in plan.warnings)


def test_low_vram_profile_uses_only_sequential_offload():
    plan = build_optimization_plan(PerformanceProfile.LOW_VRAM, capable_gpu(), 16.0)

    assert plan.sequential_offload
    assert not plan.cpu_offload
    assert plan.vae_tiling
    assert plan.vae_slicing
    assert plan.attention_slicing
    assert not plan.torch_compile


def test_high_performance_profile_rejects_insufficient_vram():
    with pytest.raises(ValueError, match="requires at least 16.0 GiB VRAM"):
        build_optimization_plan(PerformanceProfile.HIGH_PERFORMANCE, capable_gpu(8.0), 16.0)


def test_high_performance_profile_enables_available_accelerators():
    plan = build_optimization_plan(PerformanceProfile.HIGH_PERFORMANCE, capable_gpu(), 16.0)

    assert not plan.cpu_offload
    assert not plan.sequential_offload
    assert not plan.vae_tiling
    assert plan.flash_attention
    assert plan.xformers
    assert plan.torch_compile


def test_custom_profile_rejects_conflicting_offload_modes():
    with pytest.raises(ValueError, match="mutually exclusive"):
        build_optimization_plan(
            PerformanceProfile.CUSTOM,
            capable_gpu(),
            8.0,
            {"cpu_offload": True, "sequential_offload": True},
        )


def test_cpu_only_plan_contains_explicit_cuda_warning_and_disables_unavailable_features():
    capabilities = HardwareCapabilities(cuda_available=False, native_sdpa_available=False)
    plan = build_optimization_plan(
        PerformanceProfile.CUSTOM,
        capabilities,
        8.0,
        {"flash_attention": True, "xformers": True, "torch_compile": True},
    )

    assert not plan.flash_attention
    assert not plan.xformers
    assert not plan.torch_compile
    assert "CUDA is unavailable in the installed PyTorch build" in plan.warnings
