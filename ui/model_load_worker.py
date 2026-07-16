"""Qt workers that isolate long-running model operations from the GUI thread."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget

from backend.engine_manager import BackendManager
from utils.logger import get_logger

logger = get_logger("ui.model_load_worker")


class ModelLoadWorker(QThread):
    """在后台线程中加载模型，并只通过 Qt 信号返回结果。"""

    completed = Signal(bool, str)

    def __init__(
        self,
        backend: BackendManager,
        model_id: str,
        options: dict[str, Any],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._backend = backend
        self._model_id = model_id
        self._options = options

    def run(self) -> None:
        try:
            success = self._backend.load_model(
                self._model_id,
                **self._options,
            )
            message = "" if success else "模型加载失败，详情请查看日志。"
            self.completed.emit(success, message)
        except Exception as error:
            logger.exception("后台模型加载失败")
            self.completed.emit(False, str(error))


