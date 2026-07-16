"""Safe, configurable, collision-resistant output video naming."""

from __future__ import annotations

import os
import re
import string
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DEFAULT_FILENAME_PATTERN = "{timestamp}_{model}_{seed}"
_ALLOWED_FIELDS = frozenset({"timestamp", "model", "seed", "task", "task_id"})
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_RESERVATION_LOCK = threading.Lock()


class OutputFilenameError(ValueError):
    """Raised when an output filename pattern is invalid."""


def validate_filename_pattern(pattern: str) -> None:
    """Validate supported placeholders without allowing formatting expressions."""
    if not isinstance(pattern, str) or not pattern.strip():
        raise OutputFilenameError("output filename pattern cannot be empty")
    if len(pattern) > 200:
        raise OutputFilenameError("output filename pattern must not exceed 200 characters")

    try:
        parsed = list(string.Formatter().parse(pattern))
    except ValueError as error:
        raise OutputFilenameError(f"invalid output filename pattern: {error}") from error

    fields: set[str] = set()
    for _literal, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if field_name not in _ALLOWED_FIELDS:
            allowed = ", ".join(sorted(_ALLOWED_FIELDS))
            raise OutputFilenameError(
                f"unsupported output filename field: {field_name}; allowed: {allowed}"
            )
        if format_spec or conversion:
            raise OutputFilenameError(
                f"format specifiers and conversions are not allowed for field: {field_name}"
            )
        fields.add(field_name)

    if not fields:
        raise OutputFilenameError("output filename pattern must contain at least one placeholder")


def _sanitize_basename(value: str) -> str:
    """Convert rendered text to one Windows-safe filename stem."""
    sanitized = _INVALID_FILENAME_CHARS.sub("_", value)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    sanitized = re.sub(r"_+", "_", sanitized)
    if not sanitized:
        sanitized = "video"

    # Windows reserves these names even when an extension is present.
    if sanitized.upper() in _WINDOWS_RESERVED_NAMES:
        sanitized = f"_{sanitized}"

    return sanitized[:180].rstrip(" .") or "video"


def render_output_stem(
    pattern: str,
    *,
    model_id: str,
    seed: int,
    task: str,
    task_id: str = "",
    timestamp: datetime | None = None,
) -> str:
    """Render a validated pattern and return a safe filename stem."""
    validate_filename_pattern(pattern)
    rendered = pattern.format(
        timestamp=(timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S"),
        model=model_id,
        seed=seed,
        task=task,
        task_id=task_id,
    )
    return _sanitize_basename(rendered)


def _reserve_unique_path(output_dir: Path, stem: str, extension: str) -> Path:
    """Atomically reserve a unique path so concurrent workers cannot collide."""
    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    output_dir.mkdir(parents=True, exist_ok=True)

    with _RESERVATION_LOCK:
        for suffix in range(0, 10_000):
            suffix_text = "" if suffix == 0 else f"_{suffix}"
            candidate = output_dir / f"{stem}{suffix_text}{normalized_extension}"
            try:
                descriptor = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                continue
            else:
                os.close(descriptor)
                return candidate

    raise OutputFilenameError("unable to reserve a unique output filename")


@contextmanager
def reserved_output_path(
    output_dir: Path,
    pattern: str,
    *,
    model_id: str,
    seed: int,
    task: str,
    task_id: str = "",
    extension: str = ".mp4",
    timestamp: datetime | None = None,
) -> Iterator[Path]:
    """Reserve an output path and remove the placeholder if generation fails."""
    stem = render_output_stem(
        pattern,
        model_id=model_id,
        seed=seed,
        task=task,
        task_id=task_id,
        timestamp=timestamp,
    )
    path = _reserve_unique_path(output_dir, stem, extension)
    try:
        yield path
    except BaseException:
        path.unlink(missing_ok=True)
        raise
