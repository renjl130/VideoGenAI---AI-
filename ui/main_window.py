"""
VideoGenAI - 主窗口
简洁现代浅色主题UI设计
"""
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QGroupBox, QLabel, QPushButton, QLineEdit,
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QProgressBar, QListWidget, QListWidgetItem, QFileDialog,
    QStatusBar, QMenuBar, QMenu, QMessageBox, QScrollArea,
    QFrame, QGridLayout, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QFont, QAction, QColor, QPalette

from backend.engine_manager import get_backend_manager, BackendManager
from utils.task_queue import TaskType, TaskStatus
from utils.gpu_monitor import format_memory, format_gpu_info, get_gpu_monitor
from utils.logger import get_logger
from utils.i18n import I18n, t

logger = get_logger("ui")


# ==================== 简洁现代浅色主题 ====================

LIGHT_THEME = """
/* 全局 - 浅色背景 */
QMainWindow, QWidget {
    background-color: #f5f5f5;
    color: #1a1a1a;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* 分组框 - 无边框，仅用背景色区分 */
QGroupBox {
    background-color: #ffffff;
    border: none;
    border-radius: 8px;
    margin-top: 8px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
    font-size: 13px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #666666;
    font-size: 12px;
    font-weight: 600;
}

/* 按钮 - 主色调 */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton:pressed {
    background-color: #1e40af;
}

QPushButton:disabled {
    background-color: #e5e7eb;
    color: #9ca3af;
}

/* 生成按钮 - 大号醒目 */
QPushButton#generateBtn {
    background-color: #059669;
    font-size: 15px;
    font-weight: 700;
    padding: 14px 28px;
    letter-spacing: 1px;
}

QPushButton#generateBtn:hover {
    background-color: #047857;
}

/* 停止按钮 */
QPushButton#stopBtn {
    background-color: #dc2626;
}

QPushButton#stopBtn:hover {
    background-color: #b91c1c;
}

/* 次要按钮 */
QPushButton#secondaryBtn {
    background-color: #e5e7eb;
    color: #374151;
}

QPushButton#secondaryBtn:hover {
    background-color: #d1d5db;
}

/* 输入框 */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #6b7280;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #1a1a1a;
    border-radius: 6px;
}

/* 进度条 */
QProgressBar {
    background-color: #e5e7eb;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    min-height: 20px;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 4px;
}

/* 列表 */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #f3f4f6;
    border-radius: 4px;
    margin: 2px;
}

QListWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

QListWidget::item:hover {
    background-color: #f3f4f6;
}

/* 标签页 */
QTabWidget::pane {
    border: none;
    background-color: #ffffff;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: transparent;
    color: #6b7280;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 600;
}

QTabBar::tab:selected {
    color: #2563eb;
    border-bottom: 2px solid #2563eb;
}

QTabBar::tab:hover {
    color: #1a1a1a;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #d1d5db;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9ca3af;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* 标签 */
QLabel {
    color: #1a1a1a;
    background: transparent;
}

/* 复选框 */
QCheckBox {
    spacing: 8px;
    color: #374151;
    background: transparent;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #d1d5db;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

/* 状态栏 */
QStatusBar {
    background-color: #ffffff;
    color: #6b7280;
    border-top: 1px solid #e5e7eb;
    font-size: 12px;
}

/* 菜单栏 */
QMenuBar {
    background-color: #ffffff;
    color: #1a1a1a;
    border-bottom: 1px solid #e5e7eb;
    font-size: 13px;
    padding: 4px;
}

QMenuBar::item:selected {
    background-color: #f3f4f6;
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 16px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
"""


class GPUStatusWidget(QWidget):
    """GPU状态显示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_gpu_status)
        self._update_timer.start(1000)
        QTimer.singleShot(100, self._update_gpu_status)
    
    def _setup_ui(self):
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
    
    def _update_gpu_status(self):
        try:
            monitor = get_gpu_monitor()
            gpu_infos = monitor.get_all_gpu_info()
            
            if gpu_infos and len(gpu_infos) > 0:
                info = gpu_infos[0]
                self._name_label.setText(f"GPU: {info.name}")
                
                used_gb = info.used_memory / 1024
                total_gb = info.total_memory / 1024
                percent = info.memory_usage_percent
                
                self._vram_bar.setValue(int(percent))
                self._vram_label.setText(f"VRAM: {used_gb:.1f} / {total_gb:.1f} GB ({percent:.0f}%)")
                
                # 温度颜色
                temp = info.temperature
                if temp > 80:
                    temp_color = "#dc2626"
                elif temp > 60:
                    temp_color = "#f59e0b"
                else:
                    temp_color = "#6b7280"
                self._temp_label.setText(f"TEMP: {temp}°C")
                self._temp_label.setStyleSheet(f"font-size: 12px; color: {temp_color}; font-weight: 600;")
                
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


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self._backend = get_backend_manager()
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
        
        # 优化选项
        opt_group = QGroupBox(t("optimization"))
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setSpacing(8)
        
        self._cpu_offload_cb = QCheckBox(t("cpu_offload"))
        opt_layout.addWidget(self._cpu_offload_cb)
        
        self._vae_tiling_cb = QCheckBox(t("vae_tiling"))
        self._vae_tiling_cb.setChecked(True)
        opt_layout.addWidget(self._vae_tiling_cb)
        
        self._flash_attn_cb = QCheckBox(t("flash_attention"))
        self._flash_attn_cb.setChecked(True)
        opt_layout.addWidget(self._flash_attn_cb)
        
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
        
        # 任务列表
        task_tab = QWidget()
        task_layout = QVBoxLayout(task_tab)
        task_layout.setContentsMargins(8, 8, 8, 8)
        
        self._task_list = QListWidget()
        task_layout.addWidget(self._task_list)
        
        task_status_layout = QHBoxLayout()
        self._task_status_label = QLabel("")
        self._task_status_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        task_status_layout.addWidget(self._task_status_label)
        task_status_layout.addStretch()
        
        clear_btn = QPushButton(t("clear"))
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._clear_tasks)
        task_status_layout.addWidget(clear_btn)
        task_layout.addLayout(task_status_layout)
        
        self._tab_widget.addTab(task_tab, t("task_queue"))
        
        # 日志
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
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("QFrame { background-color: #ffffff; border-radius: 12px; }")
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(16, 16, 16, 16)
        bottom_layout.setSpacing(12)
        
        # Prompt输入
        prompt_row = QHBoxLayout()
        prompt_row.setSpacing(12)
        
        # 正面提示词
        prompt_left = QVBoxLayout()
        prompt_left.addWidget(QLabel(t("prompt")))
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setPlaceholderText(t("prompt_placeholder"))
        self._prompt_edit.setMinimumHeight(80)
        self._prompt_edit.setMaximumHeight(120)
        prompt_left.addWidget(self._prompt_edit)
        prompt_row.addLayout(prompt_left, 2)
        
        # 负面提示词
        prompt_right = QVBoxLayout()
        prompt_right.addWidget(QLabel(t("negative_prompt")))
        self._neg_prompt_edit = QTextEdit()
        self._neg_prompt_edit.setPlaceholderText(t("negative_placeholder"))
        self._neg_prompt_edit.setMinimumHeight(80)
        self._neg_prompt_edit.setMaximumHeight(120)
        prompt_right.addWidget(self._neg_prompt_edit)
        prompt_row.addLayout(prompt_right, 1)
        
        bottom_layout.addLayout(prompt_row)
        
        # Prompt历史 + 生成按钮
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        
        # Prompt历史
        self._history_combo = QComboBox()
        self._history_combo.setMinimumWidth(300)
        self._history_combo.addItem(t("prompt_history"))
        self._history_combo.currentTextChanged.connect(self._on_history_selected)
        action_row.addWidget(self._history_combo)
        
        refresh_btn = QPushButton(t("refresh"))
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.setFixedWidth(70)
        refresh_btn.clicked.connect(self._load_prompt_history)
        action_row.addWidget(refresh_btn)
        
        action_row.addStretch()
        
        # 按钮
        self._output_btn = QPushButton(t("open_output"))
        self._output_btn.setObjectName("secondaryBtn")
        self._output_btn.clicked.connect(self._open_output_dir)
        action_row.addWidget(self._output_btn)
        
        self._stop_btn = QPushButton(t("stop_generation"))
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_generation)
        action_row.addWidget(self._stop_btn)
        
        self._generate_btn = QPushButton(t("generate_video"))
        self._generate_btn.setObjectName("generateBtn")
        self._generate_btn.setFixedWidth(200)
        self._generate_btn.clicked.connect(self._generate)
        action_row.addWidget(self._generate_btn)
        
        bottom_layout.addLayout(action_row)
        
        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumHeight(6)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)
        bottom_layout.addWidget(self._progress_bar)
        
        right_layout.addWidget(bottom_frame)
        
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
        try:
            backend = get_backend_manager()
            available = backend.get_available_models()
            downloaded = backend.get_downloaded_models()
            
            self._model_combo.clear()
            for model_id, info in available.items():
                status = "●" if model_id in downloaded else "○"
                self._model_combo.addItem(f"{status} {info.description}", model_id)
        except Exception as e:
            logger.error(f"加载模型列表失败: {e}")
    
    def _on_model_changed(self, text):
        model_id = self._model_combo.currentData()
        if model_id:
            backend = get_backend_manager()
            info = backend.get_available_models().get(model_id)
            if info:
                self._model_info_label.setText(
                    f"{t('type')}: {info.task_type} | {t('vram_required')}: {info.vram_required}GB"
                )
    
    def _load_model(self):
        model_id = self._model_combo.currentData()
        if not model_id:
            return
        
        self._load_btn.setEnabled(False)
        self._load_btn.setText(t("loading"))
        
        try:
            backend = get_backend_manager()
            if backend.load_model(model_id):
                self._load_btn.setText(t("model_loaded"))
                self._unload_btn.setEnabled(True)
            else:
                self._load_btn.setText(t("load_model"))
                QMessageBox.warning(self, t("error"), t("load_model") + " failed")
        except Exception as e:
            self._load_btn.setText(t("load_model"))
            QMessageBox.critical(self, t("error"), str(e))
        
        self._load_btn.setEnabled(True)
    
    def _unload_model(self):
        try:
            backend = get_backend_manager()
            backend.unload_model()
            self._load_btn.setText(t("load_model"))
            self._unload_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))
    
    def _download_model(self):
        model_id = self._model_combo.currentData()
        if not model_id:
            return
        
        reply = QMessageBox.question(
            self, t("confirm"), t("confirm_download", model=model_id),
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                backend = get_backend_manager()
                if backend.download_model(model_id):
                    QMessageBox.information(self, t("success"), t("download_started"))
                else:
                    QMessageBox.warning(self, t("error"), t("download_failed"))
            except Exception as e:
                QMessageBox.critical(self, t("error"), str(e))
    
    def _load_prompt_history(self):
        try:
            backend = get_backend_manager()
            prompts = backend.get_prompt_history(limit=20)
            
            self._history_combo.clear()
            self._history_combo.addItem(t("prompt_history"))
            for p in prompts:
                text = p["prompt"][:40] + "..." if len(p["prompt"]) > 40 else p["prompt"]
                self._history_combo.addItem(text, p["prompt"])
        except Exception as e:
            logger.error(f"加载Prompt历史失败: {e}")
    
    def _on_history_selected(self, text):
        if text != t("prompt_history"):
            prompt = self._history_combo.currentData()
            if prompt:
                self._prompt_edit.setPlainText(prompt)
    
    def _random_seed(self):
        import random
        self._seed_spin.setValue(random.randint(0, 2147483647))
    
    def _generate(self):
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
            "flash_attention": self._flash_attn_cb.isChecked()
        }
        
        model_id = self._model_combo.currentData()
        
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
                **params
            )
            
            self._status_bar.showMessage(t("task_submitted", id=task_id))
            self._add_log(t("task_submitted", id=task_id), "INFO")
            
            self._current_task_id = task_id
            self._progress_timer = QTimer()
            self._progress_timer.timeout.connect(self._update_progress)
            self._progress_timer.start(500)
            
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))
            self._reset_generation_ui()
    
    def _stop_generation(self):
        if hasattr(self, '_current_task_id'):
            self._backend.cancel_task(self._current_task_id)
            self._add_log(t("task_cancelled", id=self._current_task_id), "WARNING")
        self._reset_generation_ui()
    
    def _update_progress(self):
        if not hasattr(self, '_current_task_id'):
            return
        
        status = self._backend.get_task_status(self._current_task_id)
        if status:
            progress = status.get('progress', 0)
            self._progress_bar.setValue(int(progress))
            self._status_bar.showMessage(f"{t('progress')}: {progress:.1f}%")
            
            if status['status'] in ['completed', 'failed', 'cancelled']:
                self._progress_timer.stop()
                
                if status['status'] == 'completed':
                    self._add_log(t("task_completed", id=self._current_task_id), "INFO")
                    self._status_bar.showMessage(t("generation_complete"))
                elif status['status'] == 'failed':
                    self._add_log(t("task_failed", error=status.get('error_message', '')), "ERROR")
                
                QTimer.singleShot(2000, self._reset_generation_ui)
    
    def _reset_generation_ui(self):
        self._generate_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
    
    def _update_tasks(self):
        try:
            queue = self._backend.get_task_queue()
            status = queue.get_queue_status()
            
            self._task_status_label.setText(
                t("queue_status", pending=status['pending'], running=status['running'], completed=status['completed'])
            )
            
            tasks = queue.get_all_tasks()
            if self._task_list.count() != len(tasks):
                self._task_list.clear()
                for task in tasks:
                    status_text = {
                        TaskStatus.PENDING: t("pending"),
                        TaskStatus.RUNNING: t("running"),
                        TaskStatus.COMPLETED: t("completed"),
                        TaskStatus.FAILED: t("failed"),
                        TaskStatus.CANCELLED: t("cancelled")
                    }
                    icon = status_text.get(task.status, "???")
                    progress = f" [{task.progress:.0f}%]" if task.status == TaskStatus.RUNNING else ""
                    self._task_list.addItem(f"[{icon}] {task.task_id}: {task.prompt[:30]}...{progress}")
        except:
            pass
    
    def _clear_tasks(self):
        self._backend.get_task_queue().clear_completed()
    
    def _add_log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {"DEBUG": "#6b7280", "INFO": "#e0e0e0", "WARNING": "#f59e0b", "ERROR": "#ef4444"}
        color = colors.get(level, "#e0e0e0")
        
        html = f'<span style="color: #6b7280;">[{timestamp}]</span> <span style="color: {color};">[{level}] {message}</span>'
        self._log_text.append(html)
    
    def _load_history(self):
        try:
            history = self._backend.get_history(limit=50)
            self._history_list.clear()
            for record in history:
                self._history_list.addItem(
                    f"[{record['created_at'][:16]}] {record['model_id']}: {record['prompt'][:40]}..."
                )
        except:
            pass
    
    def _clear_history(self):
        reply = QMessageBox.question(self, t("confirm"), t("confirm_clear_history"), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._backend.get_history_manager().clear_history()
            self._history_list.clear()
    
    def _open_output_dir(self):
        output_dir = Path("./outputs")
        output_dir.mkdir(exist_ok=True)
        os.startfile(str(output_dir))
    
    def _clear_cache(self):
        self._backend.clear_cache()
        self._status_bar.showMessage(t("cache_cleared"))
    
    def _change_language(self, lang: str):
        I18n.set_language(lang)
        try:
            import json
            config_path = Path("./configs/config.json")
            config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            if "app" not in config:
                config["app"] = {}
            config["app"]["language"] = lang
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except:
            pass
        
        QMessageBox.information(self, t("info"), "语言设置已保存，重启后生效。\nLanguage saved, restart to apply.")
    
    def _show_about(self):
        QMessageBox.about(self, t("about_title"), t("about_text"))
    
    def closeEvent(self, event):
        reply = QMessageBox.question(self, t("confirm"), t("confirm_exit"), QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._backend.shutdown()
            event.accept()
        else:
            event.ignore()
