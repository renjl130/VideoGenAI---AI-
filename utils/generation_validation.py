"""Generation-request validation shared by UI, backend, and engines."""

from dataclasses import dataclass
from pathlib import Path


class GenerationValidationError(ValueError):
    """Raised when a generation request violates a supported constraint."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class GenerationRequestValues:
    """Values required to validate a generation request."""

    prompt: str
    width: int
    height: int
    num_frames: int
    fps: int
    steps: int
    cfg_scale: float
    seed: int
    task_type: str = "text_to_video"
    image_path: str | None = None


def validate_generation_request(values: GenerationRequestValues) -> None:
    """Validate user-facing values against current Wan/Diffusers constraints."""
    errors: list[str] = []
    prompt = values.prompt.strip()
    if not prompt:
        errors.append("Prompt cannot be empty")
    elif len(prompt) > 4096:
        errors.append("Prompt must not exceed 4096 characters")

    for name, value in (("width", values.width), ("height", values.height)):
        if not 256 <= value <= 1920:
            errors.append(f"{name} must be between 256 and 1920")
        elif value % 16 != 0:
            errors.append(f"{name} must be divisible by 16")

    if not 1 <= values.num_frames <= 201:
        errors.append("num_frames must be between 1 and 201")
    elif (values.num_frames - 1) % 4 != 0:
        errors.append("num_frames must satisfy (num_frames - 1) % 4 == 0")

    if not 1 <= values.fps <= 60:
        errors.append("fps must be between 1 and 60")
    if not 1 <= values.steps <= 200:
        errors.append("steps must be between 1 and 200")
    if not 0.0 <= values.cfg_scale <= 30.0:
        errors.append("cfg_scale must be between 0 and 30")
    if not -1 <= values.seed <= 2**32 - 1:
        errors.append("seed must be -1 or an unsigned 32-bit integer")

    if values.task_type == "image_to_video":
        if not values.image_path:
            errors.append("image_path is required for image-to-video")
        elif not Path(values.image_path).is_file():
            errors.append("image_path does not exist or is not a file")

    if errors:
        raise GenerationValidationError(errors)
