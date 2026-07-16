from datetime import datetime
from pathlib import Path

import pytest

from utils.output_naming import (
    OutputFilenameError,
    render_output_stem,
    reserved_output_path,
    validate_filename_pattern,
)


def test_pattern_renders_supported_fields_and_sanitizes_model_id():
    stem = render_output_stem(
        "{task}_{timestamp}_{model}_{seed}_{task_id}",
        model_id="org/model:unsafe",
        seed=42,
        task="t2v",
        task_id="abc123",
        timestamp=datetime(2026, 7, 16, 12, 34, 56),
    )

    assert stem == "t2v_20260716_123456_org_model_unsafe_42_abc123"


@pytest.mark.parametrize(
    "pattern,message",
    [
        ("", "cannot be empty"),
        ("fixed-name", "at least one placeholder"),
        ("{prompt}", "unsupported output filename field"),
        ("{timestamp!r}", "conversions are not allowed"),
        ("{seed:04d}", "format specifiers"),
        ("{timestamp", "invalid output filename pattern"),
    ],
)
def test_invalid_patterns_are_rejected(pattern, message):
    with pytest.raises(OutputFilenameError, match=message):
        validate_filename_pattern(pattern)


def test_reserved_paths_are_collision_resistant(tmp_path: Path):
    kwargs = {
        "model_id": "wan",
        "seed": 7,
        "task": "t2v",
        "timestamp": datetime(2026, 7, 16, 12, 0, 0),
    }
    with reserved_output_path(tmp_path, "{timestamp}_{seed}", **kwargs) as first:
        first.write_bytes(b"first")
    with reserved_output_path(tmp_path, "{timestamp}_{seed}", **kwargs) as second:
        second.write_bytes(b"second")

    assert first.name == "20260716_120000_7.mp4"
    assert second.name == "20260716_120000_7_1.mp4"
    assert first.read_bytes() == b"first"
    assert second.read_bytes() == b"second"


def test_failed_export_removes_reserved_placeholder(tmp_path: Path):
    with pytest.raises(RuntimeError, match="encoding failed"):
        with reserved_output_path(
            tmp_path,
            "{task}_{seed}",
            model_id="wan",
            seed=9,
            task="i2v",
        ) as output_path:
            assert output_path.exists()
            raise RuntimeError("encoding failed")

    assert list(tmp_path.iterdir()) == []
