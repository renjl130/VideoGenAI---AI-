"""Prompt, history, and generation-action controls for the main window."""

from collections.abc import Callable, Iterable, Mapping

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.i18n import t


class GenerationPromptPanel(QFrame):
    """Own the prompt editors, prompt history, and generation action controls.

    The panel deliberately exposes its controls through named attributes.  This
    lets :class:`ui.main_window.MainWindow` retain legacy private aliases while
    gradually moving presentation responsibilities out of the window class.
    """

    def __init__(
        self,
        *,
        on_history_selected: Callable[[str], None],
        on_refresh_history: Callable[[], None],
        on_open_output: Callable[[], None],
        on_stop_generation: Callable[[], None],
        on_generate: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet("QFrame { background-color: #ffffff; border-radius: 12px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        prompt_row = QHBoxLayout()
        prompt_row.setSpacing(12)

        prompt_left = QVBoxLayout()
        prompt_left.addWidget(QLabel(t("prompt")))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(t("prompt_placeholder"))
        self.prompt_edit.setMinimumHeight(80)
        self.prompt_edit.setMaximumHeight(120)
        prompt_left.addWidget(self.prompt_edit)
        prompt_row.addLayout(prompt_left, 2)

        prompt_right = QVBoxLayout()
        prompt_right.addWidget(QLabel(t("negative_prompt")))
        self.negative_prompt_edit = QTextEdit()
        self.negative_prompt_edit.setPlaceholderText(t("negative_placeholder"))
        self.negative_prompt_edit.setMinimumHeight(80)
        self.negative_prompt_edit.setMaximumHeight(120)
        prompt_right.addWidget(self.negative_prompt_edit)
        prompt_row.addLayout(prompt_right, 1)

        layout.addLayout(prompt_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self.history_combo = QComboBox()
        self.history_combo.setMinimumWidth(300)
        self.history_combo.addItem(t("prompt_history"))
        self.history_combo.currentTextChanged.connect(on_history_selected)
        action_row.addWidget(self.history_combo)

        refresh_button = QPushButton(t("refresh"))
        refresh_button.setObjectName("secondaryBtn")
        refresh_button.setFixedWidth(70)
        refresh_button.clicked.connect(on_refresh_history)
        action_row.addWidget(refresh_button)

        action_row.addStretch()

        self.output_button = QPushButton(t("open_output"))
        self.output_button.setObjectName("secondaryBtn")
        self.output_button.clicked.connect(on_open_output)
        action_row.addWidget(self.output_button)

        self.stop_button = QPushButton(t("stop_generation"))
        self.stop_button.setObjectName("stopBtn")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(on_stop_generation)
        action_row.addWidget(self.stop_button)

        self.generate_button = QPushButton(t("generate_video"))
        self.generate_button.setObjectName("generateBtn")
        self.generate_button.setFixedWidth(200)
        self.generate_button.clicked.connect(on_generate)
        action_row.addWidget(self.generate_button)

        layout.addLayout(action_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def set_history_prompts(self, prompts: Iterable[Mapping[str, object]]) -> None:
        """Replace prompt-history choices without triggering a selection action.

        Refreshing history should never overwrite a prompt the user is currently
        editing.  Qt emits selection signals while a combo box is cleared, so
        those signals are temporarily blocked during the replacement.
        """
        previous_signal_state = self.history_combo.blockSignals(True)
        try:
            self.history_combo.clear()
            self.history_combo.addItem(t("prompt_history"))
            for entry in prompts:
                prompt = str(entry.get("prompt", ""))
                display_text = prompt[:40] + "..." if len(prompt) > 40 else prompt
                self.history_combo.addItem(display_text, prompt)
        finally:
            self.history_combo.blockSignals(previous_signal_state)

    def selected_history_prompt(self) -> str | None:
        """Return the selected prompt value, excluding the placeholder item."""
        prompt = self.history_combo.currentData()
        return str(prompt) if prompt else None
