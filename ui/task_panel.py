"""?????????"""

from collections.abc import Callable, Mapping, Sequence

from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from utils.i18n import t
from utils.task_queue import GenerationTask, TaskStatus


class TaskPanel(QWidget):
    """?????????????????????"""

    def __init__(self, on_clear: Callable[[], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.task_list = QListWidget()
        layout.addWidget(self.task_list)

        status_layout = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        clear_button = QPushButton(t("clear"))
        clear_button.setObjectName("secondaryBtn")
        clear_button.setFixedWidth(60)
        clear_button.clicked.connect(on_clear)
        status_layout.addWidget(clear_button)
        layout.addLayout(status_layout)

    def render_queue(
        self,
        queue_status: Mapping[str, int],
        tasks: Sequence[GenerationTask],
    ) -> None:
        """Render the queue counters and task rows without unnecessary redraws."""
        self.status_label.setText(
            t(
                "queue_status",
                pending=queue_status["pending"],
                running=queue_status["running"],
                completed=queue_status["completed"],
            )
        )
        rendered_tasks = [self._format_task(task) for task in tasks]
        current_items = [
            self.task_list.item(index).text()
            for index in range(self.task_list.count())
        ]
        if current_items == rendered_tasks:
            return

        current_row = self.task_list.currentRow()
        self.task_list.clear()
        self.task_list.addItems(rendered_tasks)
        if 0 <= current_row < self.task_list.count():
            self.task_list.setCurrentRow(current_row)

    @staticmethod
    def _format_task(task: GenerationTask) -> str:
        status_text = {
            TaskStatus.PENDING: t("pending"),
            TaskStatus.RUNNING: t("running"),
            TaskStatus.COMPLETED: t("completed"),
            TaskStatus.FAILED: t("failed"),
            TaskStatus.CANCELLED: t("cancelled"),
        }
        label = status_text.get(task.status, t("failed"))
        progress = f" [{task.progress:.0f}%]" if task.status == TaskStatus.RUNNING else ""
        return f"[{label}] {task.task_id}: {task.prompt[:30]}...{progress}"
