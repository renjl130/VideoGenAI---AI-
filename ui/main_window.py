"""
VideoGenAI - 主窗口
简洁现代浅色主题UI设计
"""

import html
import os
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend.engine_manager import get_backend_manager
from ui.generation_prompt_panel import GenerationPromptPanel
from ui.gpu_status import GPUStatusWidget
from ui.model_load_worker import ModelLoadWorker
from ui.task_panel import TaskPanel
from ui.theme import LIGHT_THEME
from utils.i18n import I18n, t
from utils.logger import get_logger
from utils.model_downloader import DownloadProgress, ModelStatus
from utils.optimization import PerformanceProfile
from utils.scheduler_registry import list_schedulers
from utils.task_queue import TaskType

# Backward-compatible public theme name used by main.py and older integrations.
ELEGANT_THEME = LIGHT_THEME

logger = get_logger("ui")


# ==================== 简洁现代浅色主题 ====================



class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._backend = get_backend_manager()
        self._model_load_worker: ModelLoadWorker | None = None
        self._download_terminal_states: dict[str, str] = {}
        self._current_task_id: str | None = None
        self._generation_session = 0
        self._pending_reset_session: int | None = None
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(500)
        self._progress_timer.timeout.connect(self._update_progress)
        self._generation_reset_timer = QTimer(self)
        self._generation_reset_timer.setSingleShot(True)
        self._generation_reset_timer.timeout.connect(self._on_generation_reset_timeout)
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()

    def _setup_ui(self):
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        self.setStyleSheet(LIGHT_THEME)

        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)

        # 主布局: 左侧面板 + 右侧内容区
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # ===== 左侧面板 =====
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # GPU状态
        gpu_group = QGroupBox(t("gpu_status"))
        gpu_layout = QVBoxLayout(gpu_group)
        self._gpu_widget = GPUStatusWidget()
        gpu_layout.addWidget(self._gpu_widget)
        left_layout.addWidget(gpu_group)

        # 模型选择
        model_group = QGroupBox(t("model_selection"))
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.setMinimumHeight(36)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(self._model_combo)

        self._model_info_label = QLabel(t("select_model"))
        self._model_info_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._model_info_label.setWordWrap(True)
        model_layout.addWidget(self._model_info_label)

        btn_row = QHBoxLayout()
        self._load_btn = QPushButton(t("load_model"))
        self._load_btn.clicked.connect(self._load_model)
        btn_row.addWidget(self._load_btn)

        self._unload_btn = QPushButton(t("unload_model"))
        self._unload_btn.setObjectName("secondaryBtn")
        self._unload_btn.clicked.connect(self._unload_model)
        self._unload_btn.setEnabled(False)
        btn_row.addWidget(self._unload_btn)
        model_layout.addLayout(btn_row)

        self._download_btn = QPushButton(t("download_model"))
        self._download_btn.setObjectName("secondaryBtn")
        self._download_btn.clicked.connect(self._download_model)
        model_layout.addWidget(self._download_btn)

        self._model_download_label = QLabel()
        self._model_download_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        self._model_download_label.setWordWrap(True)
        model_layout.addWidget(self._model_download_label)

        self._model_download_progress = QProgressBar()
        self._model_download_progress.setRange(0, 100)
        self._model_download_progress.setTextVisible(False)
        self._model_download_progress.setMaximumHeight(6)
        self._model_download_progress.setVisible(False)
        model_layout.addWidget(self._model_download_progress)

        self._cancel_download_btn = QPushButton(t("cancel_download"))
        self._cancel_download_btn.setObjectName("secondaryBtn")
        self._cancel_download_btn.clicked.connect(self._cancel_model_download)
        self._cancel_download_btn.setEnabled(False)
        model_layout.addWidget(self._cancel_download_btn)

        left_layout.addWidget(model_group)

        # 参数设置
        params_group = QGroupBox(t("generation_params"))
        params_grid = QGridLayout(params_group)
        params_grid.setSpacing(10)

        # 分辨率
        params_grid.addWidget(QLabel(t("width")), 0, 0)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(256, 1920)
        self._width_spin.setValue(832)
        self._width_spin.setSingleStep(64)
        params_grid.addWidget(self._width_spin, 0, 1)

        params_grid.addWidget(QLabel(t("height")), 0, 2)
        self._height_spin = QSpinBox()
        self._height_spin.setRange(256, 1080)
        self._height_spin.setValue(480)
        self._height_spin.setSingleStep(64)
        params_grid.addWidget(self._height_spin, 0, 3)

        # 帧数/FPS
        params_grid.addWidget(QLabel(t("frames")), 1, 0)
        self._frames_spin = QSpinBox()
        self._frames_spin.setRange(1, 200)
        self._frames_spin.setValue(81)
        params_grid.addWidget(self._frames_spin, 1, 1)

        params_grid.addWidget(QLabel(t("fps")), 1, 2)
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 30)
        self._fps_spin.setValue(16)
        params_grid.addWidget(self._fps_spin, 1, 3)

        # Steps/CFG
        params_grid.addWidget(QLabel(t("steps")), 2, 0)
        self._steps_spin = QSpinBox()
        self._steps_spin.setRange(1, 100)
        self._steps_spin.setValue(50)
        params_grid.addWidget(self._steps_spin, 2, 1)

        params_grid.addWidget(QLabel(t("cfg_scale")), 2, 2)
        self._cfg_spin = QDoubleSpinBox()
        self._cfg_spin.setRange(1.0, 20.0)
        self._cfg_spin.setValue(5.0)
        self._cfg_spin.setSingleStep(0.5)
        params_grid.addWidget(self._cfg_spin, 2, 3)

        # Seed
        params_grid.addWidget(QLabel(t("seed")), 3, 0)
        seed_row = QHBoxLayout()
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(-1, 2147483647)
        self._seed_spin.setValue(-1)
        seed_row.addWidget(self._seed_spin)

        random_btn = QPushButton(t("random"))
        random_btn.setObjectName("secondaryBtn")
        random_btn.setFixedWidth(60)
        random_btn.clicked.connect(self._random_seed)
        seed_row.addWidget(random_btn)
        params_grid.addLayout(seed_row, 3, 1, 1, 3)

        left_layout.addWidget(params_group)

        # Optimization presets resolve to safe, mutually exclusive backend plans.
        # Legacy checkboxes remain available in Custom mode for compatibility.
        opt_group = QGroupBox(t("optimization"))
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setSpacing(8)

        optimization = self._backend.get_config().optimization
        self._profile_combo = QComboBox()
        self._profile_combo.setObjectName("performanceProfileCombo")
        self._profile_combo.addItem(t("profile_balanced"), PerformanceProfile.BALANCED.value)
        self._profile_combo.addItem(t("profile_low_vram"), PerformanceProfile.LOW_VRAM.value)
        self._profile_combo.addItem(
            t("profile_high_performance"),
            PerformanceProfile.HIGH_PERFORMANCE.value,
        )
        self._profile_combo.addItem(t("profile_custom"), PerformanceProfile.CUSTOM.value)
        profile_index = self._profile_combo.findData(optimization.performance_profile)
        if profile_index < 0:
            profile_index = self._profile_combo.findData(PerformanceProfile.BALANCED.value)
        self._profile_combo.setCurrentIndex(profile_index)
        self._profile_combo.currentIndexChanged.connect(self._on_performance_profile_changed)
        opt_layout.addWidget(self._profile_combo)

        self._profile_summary_label = QLabel()
        self._profile_summary_label.setObjectName("performanceProfileSummary")
        self._profile_summary_label.setWordWrap(True)
        self._profile_summary_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        opt_layout.addWidget(self._profile_summary_label)

        scheduler_row = QHBoxLayout()
        scheduler_row.addWidget(QLabel(t("scheduler")))
        self._scheduler_combo = QComboBox()
        self._scheduler_combo.setObjectName("schedulerCombo")
        for scheduler in list_schedulers():
            self._scheduler_combo.addItem(
                scheduler.display_name,
                scheduler.scheduler_type.value,
            )
        scheduler_index = self._scheduler_combo.findData(
            self._backend.get_config().generation.scheduler
        )
        self._scheduler_combo.setCurrentIndex(max(scheduler_index, 0))
        scheduler_row.addWidget(self._scheduler_combo, 1)
        opt_layout.addLayout(scheduler_row)

        lora_row = QHBoxLayout()
        lora_row.addWidget(QLabel(t("lora")))
        self._lora_combo = QComboBox()
        self._lora_combo.setObjectName("loraCombo")
        self._lora_combo.addItem(t("lora_none"), "")
        for lora_id, lora in self._backend.get_available_loras(refresh=True).items():
            self._lora_combo.addItem(lora.name, lora_id)
        lora_row.addWidget(self._lora_combo, 1)
        self._lora_scale_spin = QDoubleSpinBox()
        self._lora_scale_spin.setObjectName("loraScaleSpin")
        self._lora_scale_spin.setRange(0.05, 2.0)
        self._lora_scale_spin.setSingleStep(0.05)
        self._lora_scale_spin.setValue(1.0)
        self._lora_scale_spin.setDecimals(2)
        self._lora_scale_spin.setEnabled(False)
        self._lora_combo.currentIndexChanged.connect(
            lambda: self._lora_scale_spin.setEnabled(bool(self._lora_combo.currentData()))
        )
        lora_row.addWidget(self._lora_scale_spin)
        opt_layout.addLayout(lora_row)

        self._cpu_offload_cb = QCheckBox(t("cpu_offload"))
        self._cpu_offload_cb.setChecked(optimization.cpu_offload)
        opt_layout.addWidget(self._cpu_offload_cb)

        self._vae_tiling_cb = QCheckBox(t("vae_tiling"))
        self._vae_tiling_cb.setChecked(optimization.vae_tiling)
        opt_layout.addWidget(self._vae_tiling_cb)

        self._flash_attn_cb = QCheckBox(t("flash_attention"))
        self._flash_attn_cb.setChecked(optimization.flash_attention)
        opt_layout.addWidget(self._flash_attn_cb)
        self._on_performance_profile_changed()

        left_layout.addWidget(opt_group)

        left_layout.addStretch()

        main_layout.addWidget(left_panel)

        # ===== 右侧内容区 =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 上半部分: 标签页（任务/日志/历史）
        self._tab_widget = QTabWidget()

        # Task list. Compatibility aliases retain the existing public widget handles.
        self._task_panel = TaskPanel(self._clear_tasks)
        self._task_list = self._task_panel.task_list
        self._task_status_label = self._task_panel.status_label
        self._tab_widget.addTab(self._task_panel, t("task_queue"))

        # Log output
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(8, 8, 8, 8)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 11))
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: none;
                border-radius: 8px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
                padding: 12px;
            }
        """)
        log_layout.addWidget(self._log_text)

        self._tab_widget.addTab(log_tab, t("log_output"))

        # 历史
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(8, 8, 8, 8)

        self._history_list = QListWidget()
        history_layout.addWidget(self._history_list)

        history_btn_layout = QHBoxLayout()
        refresh_history_btn = QPushButton(t("refresh"))
        refresh_history_btn.setObjectName("secondaryBtn")
        refresh_history_btn.clicked.connect(self._load_history)
        history_btn_layout.addWidget(refresh_history_btn)

        clear_history_btn = QPushButton(t("clear_history"))
        clear_history_btn.setObjectName("secondaryBtn")
        clear_history_btn.clicked.connect(self._clear_history)
        history_btn_layout.addWidget(clear_history_btn)
        history_layout.addLayout(history_btn_layout)

        self._tab_widget.addTab(history_tab, t("history"))

        right_layout.addWidget(self._tab_widget, 1)

        # ===== 底部: Prompt输入区 + 生成按钮 =====
        # Prompt and generation controls are isolated so their UI lifecycle can
        # evolve independently from task and backend coordination.
        self._generation_prompt_panel = GenerationPromptPanel(
            on_history_selected=self._on_history_selected,
            on_refresh_history=self._load_prompt_history,
            on_open_output=self._open_output_dir,
            on_stop_generation=self._stop_generation,
            on_generate=self._generate,
            parent=right_panel,
        )

        # Backward-compatible aliases for existing integrations and tests.
        self._prompt_edit = self._generation_prompt_panel.prompt_edit
        self._neg_prompt_edit = self._generation_prompt_panel.negative_prompt_edit
        self._history_combo = self._generation_prompt_panel.history_combo
        self._output_btn = self._generation_prompt_panel.output_button
        self._stop_btn = self._generation_prompt_panel.stop_button
        self._generate_btn = self._generation_prompt_panel.generate_button
        self._progress_bar = self._generation_prompt_panel.progress_bar

        right_layout.addWidget(self._generation_prompt_panel)

        main_layout.addWidget(right_panel)

        # 初始化
        self._load_models()
        self._load_prompt_history()
        self._load_history()

        # 任务更新定时器
        self._task_timer = QTimer()
        self._task_timer.timeout.connect(self._update_tasks)
        self._task_timer.start(1000)

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu(t("file"))
        file_menu.addAction(t("open_output"), self._open_output_dir)
        file_menu.addSeparator()
        file_menu.addAction(t("exit"), self.close)

        model_menu = menubar.addMenu(t("model"))
        model_menu.addAction(t("load_model"), self._load_model)
        model_menu.addAction(t("unload_model"), self._unload_model)
        model_menu.addAction(t("download_model"), self._download_model)

        tools_menu = menubar.addMenu(t("tools"))
        tools_menu.addAction(t("clear_cache"), self._clear_cache)

        lang_menu = menubar.addMenu(t("language"))
        lang_menu.addAction("中文", lambda: self._change_language("zh_CN"))
        lang_menu.addAction("English", lambda: self._change_language("en_US"))

        help_menu = menubar.addMenu(t("help"))
        help_menu.addAction(t("about"), self._show_about)

    def _setup_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage(t("ready"))

    def _load_models(self):
        """加载模型注册表并显示可信的本地状态。"""
        try:
            backend = self._backend
            downloader = backend.get_model_downloader()
            downloader.refresh()
            available = backend.get_available_models()

            self._model_combo.clear()
            status_icons = {
                ModelStatus.READY: "●",
                ModelStatus.INCOMPLETE: "◐",
                ModelStatus.NOT_DOWNLOADED: "○",
                ModelStatus.UNSUPPORTED: "×",
            }
            for model_id, info in available.items():
                status = backend.get_model_status(model_id)
                icon = status_icons[status]
                self._model_combo.addItem(
                    f"{icon} {info.description}",
                    model_id,
                )
        except Exception as error:
            logger.exception("加载模型列表失败")
            self._model_info_label.setText(str(error))

    def _on_model_changed(self, _text: str):
        """更新模型说明和可执行操作。"""
        model_id = self._model_combo.currentData()
        if not model_id:
            self._load_btn.setEnabled(False)
            self._download_btn.setEnabled(False)
            return

        backend = self._backend
        info = backend.get_available_models().get(model_id)
        if not info:
            return

        status = backend.get_model_status(model_id)
        status_labels = {
            ModelStatus.READY: "完整 / Ready",
            ModelStatus.INCOMPLETE: "下载未完成 / Incomplete",
            ModelStatus.NOT_DOWNLOADED: "未下载 / Not downloaded",
            ModelStatus.UNSUPPORTED: "当前版本未实现 / Unsupported",
        }
        self._model_info_label.setText(
            f"{t('type')}: {info.model_type} | "
            f"{t('vram_required')}: {info.vram_required}GB | "
            f"{status_labels[status]}"
        )
        self._load_btn.setEnabled(status is ModelStatus.READY)
        self._download_btn.setEnabled(info.implemented and status is not ModelStatus.READY)
        self._update_model_download_status()

    def _on_performance_profile_changed(self, _index: int = -1):
        """Update profile guidance and expose legacy toggles only for Custom."""
        profile = str(self._profile_combo.currentData() or PerformanceProfile.BALANCED.value)
        custom_enabled = profile == PerformanceProfile.CUSTOM.value
        for checkbox in (
            self._cpu_offload_cb,
            self._vae_tiling_cb,
            self._flash_attn_cb,
        ):
            checkbox.setEnabled(custom_enabled)

        summary_keys = {
            PerformanceProfile.BALANCED.value: "profile_balanced_summary",
            PerformanceProfile.LOW_VRAM.value: "profile_low_vram_summary",
            PerformanceProfile.HIGH_PERFORMANCE.value: "profile_high_performance_summary",
            PerformanceProfile.CUSTOM.value: "profile_custom_summary",
        }
        self._profile_summary_label.setText(
            t(summary_keys.get(profile, "profile_balanced_summary"))
        )

    def _load_model(self):
        """在后台线程中加载当前选择的模型。"""
        model_id = self._model_combo.currentData()
        if not model_id:
            return
        if self._model_load_worker and self._model_load_worker.isRunning():
            return

        self._load_btn.setEnabled(False)
        self._load_btn.setText(t("loading"))
        self._unload_btn.setEnabled(False)
        options = {
            "performance_profile": str(self._profile_combo.currentData()),
            "scheduler": str(self._scheduler_combo.currentData()),
            "lora_id": str(self._lora_combo.currentData() or ""),
            "lora_scale": self._lora_scale_spin.value(),
            "cpu_offload": self._cpu_offload_cb.isChecked(),
            "vae_tiling": self._vae_tiling_cb.isChecked(),
            "flash_attention": self._flash_attn_cb.isChecked(),
        }
        worker = ModelLoadWorker(
            self._backend,
            model_id,
            options,
            self,
        )
        worker.completed.connect(self._on_model_load_finished)
        self._model_load_worker = worker
        worker.start()

    def _on_model_load_finished(self, success: bool, message: str):
        """在 Qt 主线程中收尾模型加载 UI。"""
        worker = self._model_load_worker
        if worker is not None:
            worker.wait()
            worker.deleteLater()
            self._model_load_worker = None

        if success:
            self._load_btn.setText(t("model_loaded"))
            self._unload_btn.setEnabled(True)
            self._status_bar.showMessage(t("model_loaded"))
        else:
            self._load_btn.setText(t("load_model"))
            QMessageBox.warning(
                self,
                t("error"),
                message or t("generation_failed", error=""),
            )

        model_id = self._model_combo.currentData()
        status = self._backend.get_model_status(model_id) if model_id else None
        self._load_btn.setEnabled(status is ModelStatus.READY)

    def _unload_model(self):
        if self._model_load_worker and self._model_load_worker.isRunning():
            return
        try:
            self._backend.unload_model()
            self._load_btn.setText(t("load_model"))
            self._unload_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _download_model(self):
        """Start the selected model download after a size-aware confirmation."""
        model_id = self._model_combo.currentData()
        info = self._backend.get_available_models().get(model_id)
        if not model_id or info is None:
            return

        reply = QMessageBox.question(
            self,
            t("confirm"),
            t(
                "confirm_download",
                model=info.description,
                size=info.download_size,
            ),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            if self._backend.download_model(model_id):
                self._download_terminal_states.pop(model_id, None)
                self._status_bar.showMessage(t("download_started"))
                self._add_log(t("download_started"), "INFO")
                self._update_model_download_status()
            else:
                QMessageBox.warning(self, t("error"), t("download_failed"))
        except Exception as error:
            logger.exception("Failed to start model download")
            QMessageBox.critical(self, t("error"), str(error))

    def _cancel_model_download(self):
        """Request cancellation without blocking the Qt event loop."""
        model_id = self._model_combo.currentData()
        if not model_id:
            return

        if self._backend.cancel_model_download(model_id):
            self._status_bar.showMessage(t("download_cancel_requested"))
            self._add_log(t("download_cancel_requested"), "WARNING")
            self._update_model_download_status()

    @staticmethod
    def _format_data_size(size: int) -> str:
        """Format a byte count for compact status text."""
        if size < 1024**3:
            return f"{size / 1024**2:.1f} MiB"
        return f"{size / 1024**3:.2f} GiB"

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format an ETA without exposing implementation-specific timestamps."""
        minutes, remaining_seconds = divmod(max(0, seconds), 60)
        if minutes:
            return f"{minutes}m {remaining_seconds:02d}s"
        return f"{remaining_seconds}s"

    def _update_model_download_status(self) -> None:
        """Render the selected model download from a safe backend snapshot.

        This method is called only by Qt main-thread code and never from a
        downloader callback, so background workers cannot mutate widgets.
        """
        model_id = self._model_combo.currentData()
        if not model_id:
            self._model_download_label.clear()
            self._model_download_progress.setVisible(False)
            self._cancel_download_btn.setEnabled(False)
            return

        progress = self._backend.get_model_download_progress(model_id)
        if progress is None:
            self._model_download_label.clear()
            self._model_download_progress.setVisible(False)
            self._cancel_download_btn.setEnabled(False)
            return

        self._render_model_download_progress(progress)
        self._handle_terminal_download_state(model_id, progress)

    def _render_model_download_progress(self, progress: DownloadProgress) -> None:
        """Update status controls for one immutable progress snapshot."""
        status_key = f"download_status_{progress.status}"
        status_text = t(status_key)
        if status_text == status_key:
            status_text = progress.status

        metrics = ""
        if progress.status in {"downloading", "cancelling"} and progress.speed > 0:
            metrics = t("download_speed", speed=progress.speed)
            if progress.eta > 0:
                metrics += t("download_eta", duration=self._format_duration(progress.eta))
        if progress.error:
            metrics += t("download_error", error=progress.error[:240])

        self._model_download_label.setText(
            t(
                "download_progress",
                status=status_text,
                progress=progress.progress,
                downloaded=self._format_data_size(progress.downloaded_size),
                total=self._format_data_size(progress.total_size),
                metrics=metrics,
            )
        )
        self._model_download_progress.setValue(round(progress.progress))
        self._model_download_progress.setVisible(True)

        active = progress.status in {"pending", "downloading", "cancelling"}
        if active:
            self._download_btn.setEnabled(False)
        self._cancel_download_btn.setEnabled(progress.status in {"pending", "downloading"})

    def _handle_terminal_download_state(
        self, model_id: str, progress: DownloadProgress
    ) -> None:
        """Apply one-time UI effects after a downloader reaches a terminal state."""
        if progress.status not in {"completed", "cancelled", "failed"}:
            return
        if self._download_terminal_states.get(model_id) == progress.status:
            return
        self._download_terminal_states[model_id] = progress.status

        if progress.status == "completed":
            self._load_models()
            self._status_bar.showMessage(t("download_status_completed"))
            self._add_log(t("download_status_completed"), "INFO")
        elif progress.status == "failed":
            self._status_bar.showMessage(t("download_status_failed"))
            self._add_log(t("download_status_failed"), "ERROR")
            self._on_model_changed(self._model_combo.currentText())
        else:
            self._status_bar.showMessage(t("download_status_cancelled"))
            self._add_log(t("download_status_cancelled"), "WARNING")
            self._on_model_changed(self._model_combo.currentText())

    def _load_prompt_history(self):
        try:
            prompts = self._backend.get_prompt_history(limit=20)

            self._generation_prompt_panel.set_history_prompts(prompts)
        except Exception as e:
            logger.error(f"加载Prompt历史失败: {e}")

    def _on_history_selected(self, text):
        if text != t("prompt_history"):
            prompt = self._generation_prompt_panel.selected_history_prompt()
            if prompt:
                self._prompt_edit.setPlainText(prompt)

    def _random_seed(self):
        import random

        self._seed_spin.setValue(random.randint(0, 2147483647))

    def _generate(self):
        """Submit a generation task and begin polling its state on one timer."""
        if self._current_task_id is not None:
            logger.warning(
                "Ignoring generation request while task %s is active",
                self._current_task_id,
            )
            return

        prompt = self._prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, t("warning"), t("prompt_placeholder"))
            return

        negative_prompt = self._neg_prompt_edit.toPlainText().strip()
        params = {
            "width": self._width_spin.value(),
            "height": self._height_spin.value(),
            "num_frames": self._frames_spin.value(),
            "fps": self._fps_spin.value(),
            "steps": self._steps_spin.value(),
            "cfg_scale": self._cfg_spin.value(),
            "seed": self._seed_spin.value(),
            "cpu_offload": self._cpu_offload_cb.isChecked(),
            "vae_tiling": self._vae_tiling_cb.isChecked(),
        }
        model_id = self._model_combo.currentData()

        self._generation_reset_timer.stop()
        self._pending_reset_session = None
        self._generate_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)

        try:
            task_id = self._backend.submit_task(
                task_type=TaskType.TEXT_TO_VIDEO,
                prompt=prompt,
                negative_prompt=negative_prompt,
                model_id=model_id,
                **params,
            )
        except Exception as error:
            QMessageBox.critical(self, t("error"), str(error))
            self._reset_generation_ui()
            return

        self._generation_session += 1
        self._current_task_id = task_id
        self._status_bar.showMessage(t("task_submitted", id=task_id))
        self._add_log(t("task_submitted", id=task_id), "INFO")
        self._progress_timer.start()

    def _stop_generation(self):
        """Request cooperative cancellation and wait for the terminal state."""
        task_id = self._current_task_id
        if task_id is None:
            return

        if self._backend.cancel_task(task_id):
            self._stop_btn.setEnabled(False)
            self._add_log(t("task_cancelled", id=task_id), "WARNING")
        self._update_progress()

    def _update_progress(self):
        """Render the active task status without allowing stale timers to interfere."""
        task_id = self._current_task_id
        if task_id is None:
            return

        status = self._backend.get_task_status(task_id)
        if not status:
            logger.warning("Active generation task disappeared from queue: %s", task_id)
            self._reset_generation_ui()
            return

        progress = float(status.get("progress", 0.0))
        self._progress_bar.setValue(int(progress))
        self._status_bar.showMessage(f"{t('progress')}: {progress:.1f}%")

        terminal_statuses = {"completed", "failed", "cancelled"}
        if status.get("status") not in terminal_statuses:
            return

        self._progress_timer.stop()
        self._stop_btn.setEnabled(False)
        if status["status"] == "completed":
            self._add_log(t("task_completed", id=task_id), "INFO")
            self._status_bar.showMessage(t("generation_complete"))
        elif status["status"] == "failed":
            self._add_log(t("task_failed", error=status.get("error_message", "")), "ERROR")

        self._pending_reset_session = self._generation_session
        self._generation_reset_timer.start(2000)

    def _on_generation_reset_timeout(self) -> None:
        """Reset only the session that scheduled this delayed UI cleanup."""
        if self._pending_reset_session != self._generation_session:
            return
        self._reset_generation_ui()

    def _reset_generation_ui(self):
        """Return controls to idle and cancel all UI-only generation timers."""
        self._progress_timer.stop()
        self._generation_reset_timer.stop()
        self._current_task_id = None
        self._pending_reset_session = None
        self._generate_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setVisible(False)

    def _update_tasks(self):
        self._update_model_download_status()
        try:
            queue = self._backend.get_task_queue()
            self._task_panel.render_queue(
                queue.get_queue_status(),
                queue.get_all_tasks(),
            )
        except Exception:
            logger.exception("更新任务列表失败")

    def _clear_tasks(self):
        self._backend.get_task_queue().clear_completed()

    def _add_log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "DEBUG": "#6b7280",
            "INFO": "#e0e0e0",
            "WARNING": "#f59e0b",
            "ERROR": "#ef4444",
        }
        color = colors.get(level, "#e0e0e0")

        safe_message = html.escape(message)
        log_html = (
            f'<span style="color: #6b7280;">[{timestamp}]</span> '
            f'<span style="color: {color};">[{level}] {safe_message}</span>'
        )
        self._log_text.append(log_html)

    def _load_history(self):
        try:
            history = self._backend.get_history(limit=50)
            self._history_list.clear()
            for record in history:
                self._history_list.addItem(
                    f"[{record['created_at'][:16]}] "
                    f"{record['model_id']}: {record['prompt'][:40]}..."
                )
        except Exception:
            logger.exception("加载历史列表失败")

    def _clear_history(self):
        reply = QMessageBox.question(
            self, t("confirm"), t("confirm_clear_history"), QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._backend.get_history_manager().clear_history()
            self._history_list.clear()

    def _open_output_dir(self):
        output_dir = self._backend.get_config().resolve_path(
            "output.output_dir",
            "./outputs",
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_dir))

    def _clear_cache(self):
        self._backend.clear_cache()
        self._status_bar.showMessage(t("cache_cleared"))

    def _change_language(self, lang: str):
        if not I18n.set_language(lang):
            return
        try:
            config = self._backend.get_config()
            config.set("app.language", lang)
            config.save()
        except Exception as error:
            logger.exception("保存语言配置失败")
            QMessageBox.critical(self, t("error"), str(error))
            return

        QMessageBox.information(
            self,
            t("info"),
            "语言设置已保存，重启后生效。\nLanguage saved, restart to apply.",
        )

    def _show_about(self):
        QMessageBox.about(self, t("about_title"), t("about_text"))

    def closeEvent(self, event):
        if self._model_load_worker and self._model_load_worker.isRunning():
            QMessageBox.warning(
                self,
                t("warning"),
                "模型正在加载，请等待加载结束后再退出。",
            )
            event.ignore()
            return

        reply = QMessageBox.question(
            self, t("confirm"), t("confirm_exit"), QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._backend.shutdown()
            event.accept()
        else:
            event.ignore()
