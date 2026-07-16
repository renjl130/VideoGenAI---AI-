from pathlib import Path

import pytest
import torch
from safetensors.torch import save_file

from utils.lora_manager import LoraManager, LoraValidationError


def make_manager(root: Path) -> LoraManager:
    LoraManager._instance = None
    return LoraManager(str(root))


def write_lora(path: Path, key: str = "transformer.block.lora_A.weight") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file({key: torch.ones((1, 1))}, path)


def test_scans_nested_valid_safetensors_and_returns_stable_metadata(tmp_path: Path):
    write_lora(tmp_path / "styles" / "cinematic.safetensors")
    manager = make_manager(tmp_path)

    available = manager.get_available_loras()
    assert list(available) == ["styles/cinematic"]
    info = available["styles/cinematic"]
    assert info.name == "cinematic"
    assert info.tensor_count == 1
    assert info.path == (tmp_path / "styles" / "cinematic.safetensors").resolve()
    assert info.adapter_name.startswith("videogenai_")
    assert manager.resolve(info.lora_id) == info


def test_invalid_or_non_lora_safetensors_are_excluded(tmp_path: Path):
    write_lora(tmp_path / "not-lora.safetensors", key="transformer.weight")
    (tmp_path / "broken.safetensors").write_bytes(b"broken")
    manager = make_manager(tmp_path)

    assert manager.get_available_loras() == {}
    invalid = manager.get_invalid_loras()
    assert len(invalid) == 2
    assert any("does not contain LoRA tensors" in reason for reason in invalid.values())
    assert any("invalid safetensors checkpoint" in reason for reason in invalid.values())


def test_only_safetensors_and_registered_ids_can_be_resolved(tmp_path: Path):
    (tmp_path / "unsafe.pt").write_bytes(b"pickle")
    manager = make_manager(tmp_path)

    assert manager.get_available_loras() == {}
    with pytest.raises(KeyError, match="Unknown or invalid LoRA"):
        manager.resolve("../unsafe")
    with pytest.raises(LoraValidationError, match="only .safetensors"):
        manager.validate_file(tmp_path / "unsafe.pt")
