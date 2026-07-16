"""Cached GPU telemetry widget used by the main VideoGenAI window."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from utils.gpu_monitor import get_gpu_monitor
from utils.logger import get_logger

logger = get_logger("ui.gpu_status")


class GPUStatusWidget(QWidget):
    """GPU状态显示"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_gpu_status)
        self._update_timer.start(1000)
        QTimer.singleShot(100, self._update_gpu_status)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # GPU名称
        self._name_label = QLabel("GPU: --")
        self._name_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #1a1a1a;")
        layout.addWidget(self._name_label)

        # 显存进度条
        self._vram_bar = QProgressBar()
        self._vram_bar.setMaximumHeight(8)
        self._vram_bar.setTextVisible(False)
        layout.addWidget(self._vram_bar)

        # 显存文字
        self._vram_label = QLabel("VRAM: -- / -- GB (0%)")
        self._vram_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        layout.addWidget(self._vram_label)

        # 温度/利用率/功耗
        info_layout = QHBoxLayout()
        info_layout.setSpacing(20)

        self._temp_label = QLabel("TEMP: --°C")
        self._temp_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        info_layout.addWidget(self._temp_label)

        self._util_label = QLabel("UTIL: --%")
        self._util_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        info_layout.addWidget(self._util_label)

        self._power_label = QLabel("POWER: --W")
        self._power_label.setStyleSheet("font-size: 12px; color: #6b7280;")
        info_layout.addWidget(self._power_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

    def _update_gpu_status(self) -> None:
        try:
            monitor = get_gpu_monitor()
            gpu_infos = monitor.get_cached_gpu_info()

            if gpu_infos and len(gpu_infos) > 0:
                info = gpu_infos[0]
                self._name_label.setText(f"GPU: {info.name}")

                used_gb = info.used_memory / 1024
                total_gb = info.total_memory / 1024
                percent = info.memory_usage_percent

                self._vram_bar.setValue(int(percent))
                self._vram_label.setText(
                    f"VRAM: {used_gb:.1f} / {total_gb:.1f} GB ({percent:.0f}%)"
                )

                # 温度颜色
                temp = info.temperature
                if temp > 80:
                    temp_color = "#dc2626"
                elif temp > 60:
                    temp_color = "#f59e0b"
                else:
                    temp_color = "#6b7280"
                self._temp_label.setText(f"TEMP: {temp}°C")
                self._temp_label.setStyleSheet(
                    f"font-size: 12px; color: {temp_color}; font-weight: 600;"
                )

                self._util_label.setText(f"UTIL: {info.utilization}%")
                self._power_label.setText(f"POWER: {info.power_usage:.0f}W")
            else:
                self._name_label.setText("GPU: 未检测到")
                self._vram_bar.setValue(0)
                self._vram_label.setText("VRAM: N/A")
                self._temp_label.setText("TEMP: N/A")
                self._util_label.setText("UTIL: N/A")
                self._power_label.setText("POWER: N/A")
        except Exception as e:
            logger.error(f"GPU状态更新失败: {e}")

