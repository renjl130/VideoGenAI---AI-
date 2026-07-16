"""Download a registered VideoGenAI model in a foreground, resumable process."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.engine_manager import BackendManager, get_backend_manager  # noqa: E402
from utils.model_downloader import DownloadProgress, ModelStatus  # noqa: E402

Output = Callable[[str], None]


def _console_output(message: str) -> None:
    """Write CLI status immediately when stdout is redirected to a log file."""
    print(message, flush=True)


def _format_size(size: int) -> str:
    if size < 1024**3:
        return f"{size / 1024**2:.1f} MiB"
    return f"{size / 1024**3:.2f} GiB"


def _format_eta(seconds: int) -> str:
    minutes, seconds = divmod(max(seconds, 0), 60)
    return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"


def _progress_line(progress: DownloadProgress) -> str:
    speed = f" | {progress.speed:.1f} MiB/s" if progress.speed > 0 else ""
    eta = f" | ETA {_format_eta(progress.eta)}" if progress.eta > 0 else ""
    return (
        f"{progress.status}: {progress.progress:5.1f}% "
        f"({_format_size(progress.downloaded_size)} / {_format_size(progress.total_size)})"
        f"{speed}{eta}"
    )


def wait_for_download(
    backend: BackendManager,
    model_id: str,
    *,
    poll_interval: float = 1.0,
    output: Output = print,
) -> int:
    """Start and observe one download until it reaches a terminal state."""
    info = backend.get_available_models().get(model_id)
    if info is None:
        output(f"Unknown model ID: {model_id}")
        return 2
    if not info.implemented:
        output(f"Model is registered but not implemented: {model_id}")
        return 2
    if backend.get_model_status(model_id) is ModelStatus.READY:
        output(f"Model is already complete: {model_id}")
        return 0
    if not backend.download_model(model_id):
        output(f"Could not start model download: {model_id}")
        return 2

    output(f"Downloading {info.description} ({info.download_size:.1f} GiB).")
    last_line = ""
    while True:
        progress = backend.get_model_download_progress(model_id)
        if progress is None:
            output(
                "Download progress is unavailable; the process will stop without claiming success."
            )
            return 1

        line = _progress_line(progress)
        if line != last_line:
            output(line)
            last_line = line

        if progress.status == "completed":
            if backend.get_model_status(model_id) is ModelStatus.READY:
                output("Download completed and model integrity validation passed.")
                return 0
            output("Download completed but model integrity validation did not report READY.")
            return 1
        if progress.status == "cancelled":
            output("Download cancelled. Partial files were retained for resume.")
            return 130
        if progress.status == "failed":
            output(f"Download failed: {progress.error or 'unknown error'}")
            return 1
        time.sleep(max(0.1, poll_interval))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-id",
        help="Registered model ID (defaults to config.models.default_model)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation after the model size is displayed.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds between foreground progress snapshots (default: 1.0).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backend = get_backend_manager()
    model_id = args.model_id or backend.get_config().models.default_model
    info = backend.get_available_models().get(model_id)
    if info is None:
        _console_output(f"Unknown model ID: {model_id}")
        return 2

    _console_output(f"Model: {info.description}")
    _console_output(f"Repository payload: approximately {info.download_size:.1f} GiB")
    if not args.yes:
        if not sys.stdin.isatty():
            _console_output("Refusing non-interactive download without --yes.")
            return 2
        answer = input("Start or resume this download? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            _console_output("Download not started.")
            return 0

    try:
        return wait_for_download(
            backend,
            model_id,
            poll_interval=args.poll_interval,
            output=_console_output,
        )
    except KeyboardInterrupt:
        if backend.cancel_model_download(model_id):
            _console_output("Cancellation requested. Re-run this command later to resume.")
        else:
            _console_output("Interrupted before an active model download could be cancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
