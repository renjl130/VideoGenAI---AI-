"""
VideoGenAI - 主窗口
高级黑白线条风格UI设计
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


# ==================== 高级黑白线条主题 ====================

ELEGANT_THEME = """
/* 全局 - 纯黑背景 */
QMainWindow, QWidget {
    background-color: #000000;
    color: #ffffff;
    font-family: "Segoe UI", "Microsoft YaHei", "Arial";
    font-size: 13px;
}

/* 分组框 - 细线边框 */
QGroupBox {
    background-color: transparent;
    border: 1px solid #333333;
    border-radius: 2px;
    margin-top: 12px;
    padding: 16px 10px 10px 10px;
    font-weight: 400;
    font-size: 12px;
    color: #888888;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* 按钮 - 白色边框风格 */
QPushButton {
    background-color: transparent;
    color: #ffffff;
    border: 1px solid #444444;
    padding: 8px 16px;
    border-radius: 1px;
    font-weight: 500;
    font-size: 12px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #ffffff;
    color: #000000;
    border-color: #ffffff;
}

QPushButton:pressed {
    background-color: #cccccc;
    color: #000000;
}

QPushButton:disabled {
    border-color: #222222;
    color: #444444;
}

/* 主按钮 - 白色填充 */
QPushButton#generateBtn {
    background-color: #ffffff;
    color: #000000;
    font-size: 14px;
    font-weight: 700;
    padding: 12px 24px;
    letter-spacing: 2px;
}

QPushButton#generateBtn:hover {
    background-color: #e0e0e0;
}

/* 停止按钮 - 红色边框 */
QPushButton#stopBtn {
    border-color: #ff4444;
    color: #ff4444;
}

QPushButton#stopBtn:hover {
    background-color: #ff4444;
    color: #ffffff;
}

/* 次要按钮 */
QPushButton#secondaryBtn {
    border-color: #333333;
    color: #888888;
}

QPushButton#secondaryBtn:hover {
    border-color: #ffffff;
    color: #ffffff;
}

/* 输入框 - 极简线条 */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0a0a0a;
    color: #ffffff;
    border: 1px solid #333333;
    border-radius: 1px;
    padding: 8px 10px;
    font-size: 13px;
    selection-background-color: #ffffff;
    selection-color: #000000;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #ffffff;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #ffffff;
}

QComboBox QAbstractItemView {
    background-color: #0a0a0a;
    border: 1px solid #333333;
    selection-background-color: #ffffff;
    selection-color: #000000;
    color: #ffffff;
}

/* 进度条 - 黑白 */
QProgressBar {
    background-color: #111111;
    border: 1px solid #333333;
    border-radius: 1px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    min-height: 20px;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #ffffff;
}

/* 列表 - 简洁线条 */
QListWidget {
    background-color: #050505;
    border: 1px solid #222222;
    border-radius: 1px;
    padding: 2px;
}

QListWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #111111;
    margin: 1px;
}

QListWidget::item:selected {
    background-color: #ffffff;
    color: #000000;
}

QListWidget::item:hover {
    background-color: #111111;
}

/* 标签页 */
QTabWidget::pane {
    border: 1px solid #333333;
    background-color: #000000;
}

QTabBar::tab {
    background-color: transparent;
    color: #666666;
    padding: 8px 16px;
    border: 1px solid #333333;
    border-bottom: none;
    margin-right: 1px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QTabBar::tab:selected {
    background-color: #000000;
    color: #ffffff;
    border-bottom: 1px solid #000000;
}

QTabBar::tab:hover {
    color: #ffffff;
}

/* 滚动条 - 极细 */
QScrollBar:vertical {
    background-color: #000000;
    width: 6px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #333333;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #666666;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* 标签 */
QLabel {
    color: #ffffff;
    background: transparent;
}

/* 复选框 */
QCheckBox {
    spacing: 8px;
    color: #cccccc;
    background: transparent;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #444444;
    border-radius: 1px;
    background-color: transparent;
}

QCheckBox::indicator:checked {
    background-color: #ffffff;
    border-color: #ffffff;
}

/* 分割器 */
QSplitter::handle {
    background-color: #222222;
    width: 1px;
}

/* 状态栏 */
QStatusBar {
    background-color: #000000;
    color: #666666;
    border-top: 1px solid #222222;
    font-size: 11px;
}

/* 菜单栏 */
QMenuBar {
    background-color: #000000;
    color: #ffffff;
    border-bottom: 1px solid #222222;
    font-size: 12px;
}

QMenuBar::item:selected {
    background-color: #222222;
}

QMenu {
    background-color: #0a0a0a;
    border: 1px solid #333333;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px;
}

QMenu::item:selected {
    background-color: #ffffff;
    color: #000000;
}
"""


class GPUStatusWidget(QWidget):
    """GPU状态显示 - 实时更新"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_gpu_status)
        self._update_timer.start(1000)  # 每秒更新
        
        # 立即更新一次
        QTimer.singleShot(100, self._update_gpu_status)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # GPU名称
        self._name_label = QLabel("GPU: --")
        self._name_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #ffffff;")
        layout.addWidget(self._name_label)
        
        # 显存使用
        mem_layout = QHBoxLayout()
        mem_layout.setSpacing(8)
        
        self._vram_label = QLabel("VRAM: -- / -- GB")
        self._vram_label.setStyleSheet("font-size: 11px; color: #888888;")
        mem_layout.addWidget(self._vram_label)
        
        self._vram_percent = QLabel("(0%)")
        self._vram_percent.setStyleSheet("font-size: 11px; color: #666666;")
        mem_layout.addWidget(self._vram_percent)
        
        mem_layout.addStretch()
        layout.addLayout(mem_layout)
        
        # 进度条
        self._vram_bar = QProgressBar()
        self._vram_bar.setMaximumHeight(4)
        self._vram_bar.setTextVisible(False)
        self._vram_bar.setStyleSheet("""
            QProgressBar { background-color: #222222; border: none; }
            QProgressBar::chunk { background-color: #ffffff; }
        """)
        layout.addWidget(self._vram_bar)
        
        # 温度/利用率/功耗
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        
        self._temp_label = QLabel("TEMP: --°C")
        self._temp_label.setStyleSheet("font-size: 11px; color: #888888;")
        info_layout.addWidget(self._temp_label)
        
        self._util_label = QLabel("UTIL: --%")
        self._util_label.setStyleSheet("font-size: 11px; color: #888888;")
        info_layout.addWidget(self._util_label)
        
        self._power_label = QLabel("POWER: --W")
        self._power_label.setStyleSheet("font-size: 11px; color: #888888;")
        info_layout.addWidget(self._power_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
    
    def _update_gpu_status(self):
        """更新GPU状态"""
        try:
            monitor = get_gpu_monitor()
            gpu_infos = monitor.get_all_gpu_info()
            
            if gpu_infos and len(gpu_infos) > 0:
                info = gpu_infos[0]
                
                # GPU名称
                self._name_label.setText(f"GPU: {info.name}")
                
                # 显存
                used_gb = info.used_memory / 1024
                total_gb = info.total_memory / 1024
                percent = info.memory_usage_percent
                
                self._vram_label.setText(f"VRAM: {used_gb:.1f} / {total_gb:.1f} GB")
                self._vram_percent.setText(f"({percent:.0f}%)")
                self._vram_bar.setValue(int(percent))
                
                # 温度 - 根据温度改变颜色
                temp = info.temperature
                if temp > 80:
                    temp_color = "#ff4444"
                elif temp > 60:
                    temp_color = "#ffaa00"
                else:
                    temp_color = "#888888"
                self._temp_label.setText(f"TEMP: {temp}°C")
                self._temp_label.setStyleSheet(f"font-size: 11px; color: {temp_color};")
                
                # 利用率
                util = info.utilization
                self._util_label.setText(f"UTIL: {util}%")
                
                # 功耗
                power = info.power_usage
                self._power_label.setText(f"POWER: {power:.0f}W")
                
            else:
                self._name_label.setText("GPU: 未检测到")
                self._vram_label.setText("VRAM: N/A")
                self._vram_percent.setText("")
                self._vram_bar.setValue(0)
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
        
        # 应用主题
        self.setStyleSheet(ELEGANT_THEME)
        
        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)
        
        # 主布局 - 左右分栏
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # ===== 左侧面板 =====
        left_panel = QWidget()
        left_panel.setFixedWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        # GPU状态栏
        gpu_frame = QFrame()
        gpu_frame.setStyleSheet("QFrame { border: 1px solid #333333; padding: 8px; }")
        gpu_layout = QVBoxLayout(gpu_frame)
        gpu_layout.setContentsMargins(8, 8, 8, 8)
        
        self._gpu_widget = GPUStatusWidget()
        gpu_layout.addWidget(self._gpu_widget)
        left_layout.addWidget(gpu_frame)
        
        # 模型选择
        model_group = QGroupBox(t("model_selection"))
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(8)
        
        self._model_combo = QComboBox()
        self._model_combo.setMinimumHeight(36)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        model_layout.addWidget(self._model_combo)
        
        self._model_info_label = QLabel(t("select_model"))
        self._model_info_label.setStyleSheet("color: #666666; font-size: 11px;")
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
        
        # Prompt输入 - 大尺寸
        prompt_group = QGroupBox(t("prompt"))
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setSpacing(6)
        
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setPlaceholderText(t("prompt_placeholder"))
        self._prompt_edit.setMinimumHeight(120)
        self._prompt_edit.setMaximumHeight(200)
        prompt_layout.addWidget(self._prompt_edit)
        
        # Prompt历史
        history_row = QHBoxLayout()
        self._history_combo = QComboBox()
        self._history_combo.addItem(t("prompt_history"))
        self._history_combo.currentTextChanged.connect(self._on_history_selected)
        history_row.addWidget(self._history_combo)
        
        refresh_btn = QPushButton(t("refresh"))
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.setFixedWidth(60)
        refresh_btn.clicked.connect(self._load_prompt_history)
        history_row.addWidget(refresh_btn)
        prompt_layout.addLayout(history_row)
        
        left_layout.addWidget(prompt_group)
        
        # Negative Prompt
        neg_group = QGroupBox(t("negative_prompt"))
        neg_layout = QVBoxLayout(neg_group)
        
        self._neg_prompt_edit = QTextEdit()
        self._neg_prompt_edit.setPlaceholderText(t("negative_placeholder"))
        self._neg_prompt_edit.setMinimumHeight(60)
        self._neg_prompt_edit.setMaximumHeight(100)
        neg_layout.addWidget(self._neg_prompt_edit)
        
        left_layout.addWidget(neg_group)
        
        # 参数设置 - 紧凑布局
        params_group = QGroupBox(t("generation_params"))
        params_grid = QGridLayout(params_group)
        params_grid.setSpacing(8)
        
        # 第一行: 分辨率
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
        
        # 第二行: 帧数/FPS
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
        
        # 第三行: Steps/CFG
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
        
        # 第四行: Seed
        params_grid.addWidget(QLabel(t("seed")), 3, 0)
        seed_row = QHBoxLayout()
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(-1, 2147483647)
        self._seed_spin.setValue(-1)
        seed_row.addWidget(self._seed_spin)
        
        random_btn = QPushButton(t("random"))
        random_btn.setObjectName("secondaryBtn")
        random_btn.setFixedWidth(50)
        random_btn.clicked.connect(self._random_seed)
        seed_row.addWidget(random_btn)
        params_grid.addLayout(seed_row, 3, 1, 1, 3)
        
        left_layout.addWidget(params_group)
        
        # 优化选项
        opt_group = QGroupBox(t("optimization"))
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setSpacing(6)
        
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
        
        # 底部按钮
        self._generate_btn = QPushButton(t("generate_video"))
        self._generate_btn.setObjectName("generateBtn")
        self._generate_btn.clicked.connect(self._generate)
        left_layout.addWidget(self._generate_btn)
        
        self._stop_btn = QPushButton(t("stop_generation"))
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_generation)
        left_layout.addWidget(self._stop_btn)
        
        self._output_btn = QPushButton(t("open_output"))
        self._output_btn.setObjectName("secondaryBtn")
        self._output_btn.clicked.connect(self._open_output_dir)
        left_layout.addWidget(self._output_btn)
        
        main_layout.addWidget(left_panel)
        
        # ===== 右侧面板 =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # 标签页
        self._tab_widget = QTabWidget()
        
        # 任务列表
        task_tab = QWidget()
        task_layout = QVBoxLayout(task_tab)
        task_layout.setContentsMargins(8, 8, 8, 8)
        
        self._task_list = QListWidget()
        task_layout.addWidget(self._task_list)
        
        task_status_layout = QHBoxLayout()
        self._task_status_label = QLabel("")
        self._task_status_label.setStyleSheet("color: #666666; font-size: 11px;")
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
        self._log_text.setFont(QFont("Consolas", 10))
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: #050505;
                border: 1px solid #222222;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 11px;
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
        
        right_layout.addWidget(self._tab_widget)
        
        # 进度条
        self._progress_frame = QFrame()
        self._progress_frame.setStyleSheet("QFrame { border: 1px solid #333333; }")
        self._progress_frame.setVisible(False)
        progress_layout = QVBoxLayout(self._progress_frame)
        progress_layout.setContentsMargins(8, 8, 8, 8)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumHeight(16)
        self._progress_bar.setTextVisible(True)
        progress_layout.addWidget(self._progress_bar)
        
        self._progress_label = QLabel("")
        self._progress_label.setAlignment(Qt.AlignCenter)
        self._progress_label.setStyleSheet("color: #888888; font-size: 11px;")
        progress_layout.addWidget(self._progress_label)
        
        right_layout.addWidget(self._progress_frame)
        
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
                    f"{t('type')}: {info.task_type} | {t('resolution')}: {info.resolution} | "
                    f"{t('vram_required')}: {info.vram_required}GB | {t('license')}: {info.license}"
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
            self, t("confirm"),
            t("confirm_download", model=model_id),
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
                text = p["prompt"][:35] + "..." if len(p["prompt"]) > 35 else p["prompt"]
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
        self._progress_frame.setVisible(True)
        self._progress_bar.setValue(0)
        self._progress_label.setText(t("generating"))
        
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
            self._progress_label.setText(f"{t('progress')}: {progress:.1f}%")
            
            if status['status'] in ['completed', 'failed', 'cancelled']:
                self._progress_timer.stop()
                
                if status['status'] == 'completed':
                    self._progress_label.setText(t("generation_complete"))
                    self._progress_label.setStyleSheet("color: #00ff00; font-size: 11px;")
                    self._add_log(t("task_completed", id=self._current_task_id), "INFO")
                elif status['status'] == 'failed':
                    self._progress_label.setText(t("generation_failed", error=status.get('error_message', '')))
                    self._progress_label.setStyleSheet("color: #ff4444; font-size: 11px;")
                    self._add_log(t("task_failed", error=status.get('error_message', '')), "ERROR")
                
                QTimer.singleShot(3000, self._reset_generation_ui)
    
    def _reset_generation_ui(self):
        self._generate_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_frame.setVisible(False)
    
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
        colors = {"DEBUG": "#666666", "INFO": "#ffffff", "WARNING": "#ffaa00", "ERROR": "#ff4444"}
        color = colors.get(level, "#ffffff")
        
        html = f'<span style="color: #444444;">[{timestamp}]</span> <span style="color: {color};">[{level}] {message}</span>'
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
