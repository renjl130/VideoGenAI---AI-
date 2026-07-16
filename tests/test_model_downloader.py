import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from utils.model_downloader import (
    SUPPORTED_MODELS,
    DownloadProgress,
    ModelDownloader,
    ModelStatus,
)


class ModelValidationTests(unittest.TestCase):
    @staticmethod
    def _write_model_layout(model_path: Path) -> None:
        files = {
            "model_index.json": b"{}",
            "scheduler/scheduler_config.json": b"{}",
            "text_encoder/config.json": b"{}",
            "text_encoder/model.safetensors.index.json": (
                b'{"weight_map": {"encoder": "model-00001-of-00001.safetensors"}}'
            ),
            "text_encoder/model-00001-of-00001.safetensors": b"weight",
            "tokenizer/tokenizer_config.json": b"{}",
            "tokenizer/tokenizer.json": b"{}",
            "transformer/config.json": b"{}",
            "transformer/diffusion_pytorch_model.safetensors.index.json": (
                b'{"weight_map": {'
                b'"transformer": "diffusion_pytorch_model-00001-of-00001.safetensors"}}'
            ),
            "transformer/diffusion_pytorch_model-00001-of-00001.safetensors": b"weight",
            "vae/config.json": b"{}",
            "vae/diffusion_pytorch_model.safetensors": b"weight",
        }
        for relative_path, content in files.items():
            target = model_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def test_diffusers_layout_requires_real_weight_artifacts(self):
        model_id = "wan2.1-t2v-1.3b"
        info = SUPPORTED_MODELS[model_id]
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / model_id
            self._write_model_layout(model_path)

            self.assertIs(
                ModelDownloader._inspect_model_path(model_path, info),
                ModelStatus.READY,
            )

            (model_path / "transformer/diffusion_pytorch_model.safetensors.index.json").unlink()
            self.assertIs(
                ModelDownloader._inspect_model_path(model_path, info),
                ModelStatus.INCOMPLETE,
            )

    def test_weight_index_requires_every_referenced_shard(self):
        model_id = "wan2.1-t2v-1.3b"
        info = SUPPORTED_MODELS[model_id]
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / model_id
            self._write_model_layout(model_path)
            (model_path / "text_encoder/model-00001-of-00001.safetensors").unlink()

            self.assertIs(
                ModelDownloader._inspect_model_path(model_path, info),
                ModelStatus.INCOMPLETE,
            )

    def test_interrupted_download_is_incomplete_even_with_model_files(self):
        model_id = "wan2.1-t2v-1.3b"
        info = SUPPORTED_MODELS[model_id]
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / model_id
            self._write_model_layout(model_path)
            cache = model_path / ".cache" / "huggingface" / "download"
            cache.mkdir(parents=True)
            (cache / "weights.incomplete").touch()
            self.assertIs(
                ModelDownloader._inspect_model_path(model_path, info),
                ModelStatus.INCOMPLETE,
            )

    def test_progress_snapshot_is_detached(self):
        progress = DownloadProgress("wan2.1-t2v-1.3b", 100)
        progress.update_downloaded_size(50)
        snapshot = progress.snapshot()
        progress.update_downloaded_size(75)

        self.assertEqual(snapshot.downloaded_size, 50)
        self.assertEqual(snapshot.progress, 50.0)
        self.assertEqual(progress.downloaded_size, 75)

    def test_size_calculation_excludes_stale_non_diffusers_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            payload = model_path / "transformer" / "weights.safetensors"
            payload.parent.mkdir(parents=True)
            payload.write_bytes(b"1234")
            (model_path / "legacy_model.pth").write_bytes(b"x" * 1024)
            cache_file = model_path / ".cache" / "download" / "chunk"
            cache_file.parent.mkdir(parents=True)
            cache_file.write_bytes(b"x" * 1024)

            self.assertEqual(ModelDownloader._directory_size(model_path), 4)

    def test_size_calculation_counts_only_current_diffusers_cache_partials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            payload = model_path / "transformer" / "weights.safetensors"
            payload.parent.mkdir(parents=True)
            payload.write_bytes(b"1234")

            cache_root = model_path / ".cache" / "huggingface" / "download"
            session_start = datetime.now()
            current_partial = cache_root / "transformer" / "weights.incomplete"
            current_partial.parent.mkdir(parents=True)
            current_partial.write_bytes(b"x" * 7)
            stale_partial = cache_root / "text_encoder" / "stale.incomplete"
            stale_partial.parent.mkdir(parents=True)
            stale_partial.write_bytes(b"x" * 11)
            unrelated_partial = cache_root / "assets" / "asset.incomplete"
            unrelated_partial.parent.mkdir(parents=True)
            unrelated_partial.write_bytes(b"x" * 13)

            stale_timestamp = (datetime.now() - timedelta(minutes=5)).timestamp()
            os.utime(stale_partial, (stale_timestamp, stale_timestamp))

            self.assertEqual(
                ModelDownloader._directory_size(model_path, cache_since=session_start),
                11,
            )


if __name__ == "__main__":
    unittest.main()
