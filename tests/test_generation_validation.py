from pathlib import Path

import pytest

from utils.generation_validation import (
    GenerationRequestValues,
    GenerationValidationError,
    validate_generation_request,
)


def valid_values(**overrides):
    values = {
        "prompt": "A calm ocean at sunrise",
        "width": 832,
        "height": 480,
        "num_frames": 81,
        "fps": 16,
        "steps": 50,
        "cfg_scale": 5.0,
        "seed": -1,
    }
    values.update(overrides)
    return GenerationRequestValues(**values)


def test_valid_wan_request_is_accepted():
    validate_generation_request(valid_values())


@pytest.mark.parametrize("field,value", [("width", 833), ("height", 478)])
def test_resolution_must_be_divisible_by_16(field, value):
    with pytest.raises(GenerationValidationError, match=f"{field} must be divisible by 16"):
        validate_generation_request(valid_values(**{field: value}))


@pytest.mark.parametrize("num_frames", [2, 80, 82, 200])
def test_frame_count_must_follow_wan_four_n_plus_one_constraint(num_frames):
    with pytest.raises(GenerationValidationError, match=r"\(num_frames - 1\) % 4 == 0"):
        validate_generation_request(valid_values(num_frames=num_frames))


def test_image_to_video_requires_existing_input(tmp_path: Path):
    missing = tmp_path / "missing.png"
    with pytest.raises(GenerationValidationError, match="image_path does not exist"):
        validate_generation_request(
            valid_values(task_type="image_to_video", image_path=str(missing))
        )


def test_validation_reports_multiple_user_errors_together():
    with pytest.raises(GenerationValidationError) as captured:
        validate_generation_request(valid_values(prompt="", width=833, fps=0))

    assert captured.value.errors == [
        "Prompt cannot be empty",
        "width must be divisible by 16",
        "fps must be between 1 and 60",
    ]
