from unittest.mock import patch

import torch

from utils.inference_errors import (
    CudaMemorySnapshot,
    InferenceErrorKind,
    InferenceErrorReport,
    classify_inference_error,
)


def test_cuda_oom_is_classified_with_snapshot_and_cleanup():
    snapshot = CudaMemorySnapshot(
        device_id=0,
        allocated_mib=7000,
        reserved_mib=7600,
        peak_allocated_mib=7800,
        free_mib=100,
        total_mib=8192,
    )
    with (
        patch("utils.inference_errors.capture_cuda_memory", return_value=snapshot),
        patch("utils.inference_errors.recover_cuda_memory", return_value=True) as cleanup,
    ):
        report = classify_inference_error(
            torch.OutOfMemoryError("CUDA out of memory"),
            phase="t2v_generation",
            device_id=0,
        )

    assert report.kind is InferenceErrorKind.CUDA_OOM
    assert report.recoverable
    assert report.memory == snapshot
    assert report.details["cleanup_succeeded"] is True
    assert "低显存档位" in report.user_message
    cleanup.assert_called_once_with(0)


def test_cuda_oom_message_fallback_works_for_wrapped_runtime_error():
    report = classify_inference_error(
        RuntimeError("CUDA error: out of memory"),
        phase="model_load",
        cleanup_oom=False,
    )

    assert report.kind is InferenceErrorKind.CUDA_OOM
    assert report.details["cleanup_succeeded"] is False


def test_error_report_round_trip_preserves_unknown_compatible_data():
    original = InferenceErrorReport(
        kind=InferenceErrorKind.RUNTIME,
        phase="generation",
        user_message="failed",
        technical_message="details",
        recoverable=True,
        details={"attempt": 2},
    )

    restored = InferenceErrorReport.from_dict(original.to_dict())
    assert restored == original


def test_common_error_categories_have_stable_user_messages():
    dependency = classify_inference_error(ImportError("missing peft"), phase="model_load")
    validation = classify_inference_error(ValueError("bad width"), phase="generation")
    file_system = classify_inference_error(FileNotFoundError("missing model"), phase="model_load")

    assert dependency.kind is InferenceErrorKind.DEPENDENCY
    assert validation.kind is InferenceErrorKind.VALIDATION
    assert validation.user_message == "bad width"
    assert file_system.kind is InferenceErrorKind.FILE_SYSTEM
