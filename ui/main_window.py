"""
VideoGenAI - 主窗口
现代化深色主题UI设计
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
    QFrame, QGridLayout, QSizePolicy, QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QFont, QColor, QPalette, QAction, QLinearGradient, QPainter

from backend.engine_manager import get_backend_manager, BackendManager
from utils.task_queue import TaskType, TaskStatus
from utils.gpu_monitor import format_memory, format_gpu_info
from utils.logger import get_logger

logger = get_logger("ui")


# ==================== 现代化深色主题 ====================

MODERN_DARK_THEME = """
/* 全局样式 */
QMainWindow {
    background-color: #0f0f0f;
}

QWidget {
    background-color: #0f0f0f;
    color: #e0e0e0;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* 分组框 */
QGroupBox {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    margin-top: 14px;
    padding: 18px 12px 12px 12px;
    font-weight: 600;
    font-size: 13px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: #7c8aff;
    font-size: 14px;
}

/* 按钮基础样式 */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #6d28d9);
}

QPushButton:disabled {
    background-color: #2a2a3e;
    color: #555;
}

/* 生成按钮 - 特殊样式 */
QPushButton#generateBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
    font-size: 16px;
    padding: 14px 28px;
    min-height: 30px;
}

QPushButton#generateBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
}

/* 停止按钮 */
QPushButton#stopBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #dc2626);
}

QPushButton#stopBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f87171, stop:1 #ef4444);
}

/* 次要按钮 */
QPushButton#secondaryBtn {
    background: #2a2a3e;
    border: 1px solid #3a3a5e;
}

QPushButton#secondaryBtn:hover {
    background: #3a3a5e;
}

/* 输入框 */
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #16162a;
    color: #e0e0e0;
    border: 2px solid #2a2a4a;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    selection-background-color: #4f46e5;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #7c8aff;
    background-color: #1a1a30;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid #7c8aff;
}

QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    border: 1px solid #3a3a5e;
    selection-background-color: #4f46e5;
    color: #e0e0e0;
}

/* 进度条 */
QProgressBar {
    background-color: #16162a;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    text-align: center;
    color: white;
    font-weight: 600;
    min-height: 24px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
    border-radius: 7px;
}

/* 列表 */
QListWidget {
    background-color: #16162a;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    padding: 10px 12px;
    border-bottom: 1px solid #1a1a2e;
    border-radius: 6px;
    margin: 2px;
}

QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
    color: white;
}

QListWidget::item:hover {
    background-color: #1e1e36;
}

/* 标签页 */
QTabWidget::pane {
    border: 1px solid #2a2a4a;
    background-color: #1a1a2e;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #16162a;
    color: #888;
    padding: 10px 20px;
    border: 1px solid #2a2a4a;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #1a1a2e;
    color: #7c8aff;
    border-bottom: 2px solid #7c8aff;
}

QTabBar::tab:hover {
    background-color: #1e1e36;
    color: #e0e0e0;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: #0f0f0f;
    width: 10px;
    border: none;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #3a3a5e;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #7c8aff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* 标签 */
QLabel {
    color: #e0e0e0;
}

QLabel#titleLabel {
    font-size: 24px;
    font-weight: 700;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c8aff, stop:1 #c084fc);
    -webkit-background-clip: text;
    color: transparent;
}

QLabel#subtitleLabel {
    color: #888;
    font-size: 12px;
}

QLabel#sectionLabel {
    color: #7c8aff;
    font-weight: 600;
    font-size: 14px;
}

/* 复选框 */
QCheckBox {
    spacing: 8px;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #3a3a5e;
    background-color: #16162a;
}

QCheckBox::indicator:checked {
    background-color: #4f46e5;
    border-color: #7c8aff;
}

QCheckBox::indicator:hover {
    border-color: #7c8aff;
}

/* 分割器 */
QSplitter::handle {
    background-color: #2a2a4a;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #7c8aff;
}

/* 状态栏 */
QStatusBar {
    background-color: #16162a;
    color: #888;
    border-top: 1px solid #2a2a4a;
    font-size: 12px;
}

/* 菜单栏 */
QMenuBar {
    background-color: #16162a;
    color: #e0e0e0;
    border-bottom: 1px solid #2a2a4a;
}

QMenuBar::item:selected {
    background-color: #2a2a4a;
}

QMenu {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #4f46e5;
}

/* 工具提示 */
QToolTip {
    background-color: #1a1a2e;
    color: #e0e0e0;
    border: 1px solid #3a3a5e;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""


class StyledCard(QFrame):
    """现代化卡片组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 1px solid #2a2a4a;
                border-radius: 12px;
                padding: 12px;
            }
        """)


class GPUStatusCard(StyledCard):
    """GPU状态卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_status)
        self._update_timer.start(2000)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("GPU Status")
        title.setProperty("class", "sectionLabel")
        title.setStyleSheet("color: #7c8aff; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        # GPU名称
        self._gpu_name = QLabel("Detecting GPU...")
        self._gpu_name.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(self._gpu_name)
        
        # 显存进度条
        mem_layout = QVBoxLayout()
        
        mem_header = QHBoxLayout()
        mem_header.addWidget(QLabel("VRAM"))
        self._mem_percent = QLabel("0%")
        self._mem_percent.setStyleSheet("color: #7c8aff; font-weight: 600;")
        mem_header.addWidget(self._mem_percent, alignment=Qt.AlignRight)
        mem_layout.addLayout(mem_header)
        
        self._mem_bar = QProgressBar()
        self._mem_bar.setMaximumHeight(12)
        self._mem_bar.setTextVisible(False)
        mem_layout.addWidget(self._mem_bar)
        
        self._mem_text = QLabel("0 / 0 GB")
        self._mem_text.setStyleSheet("color: #888; font-size: 12px;")
        mem_layout.addWidget(self._mem_text)
        
        layout.addLayout(mem_layout)
        
        # 详细信息网格
        info_grid = QGridLayout()
        info_grid.setSpacing(8)
        
        # 温度
        info_grid.addWidget(self._create_icon_label("Temperature:"), 0, 0)
        self._temp_label = QLabel("-- °C")
        self._temp_label.setStyleSheet("font-weight: 600;")
        info_grid.addWidget(self._temp_label, 0, 1)
        
        # 利用率
        info_grid.addWidget(self._create_icon_label("Utilization:"), 1, 0)
        self._util_label = QLabel("-- %")
        self._util_label.setStyleSheet("font-weight: 600;")
        info_grid.addWidget(self._util_label, 1, 1)
        
        # 功耗
        info_grid.addWidget(self._create_icon_label("Power:"), 2, 0)
        self._power_label = QLabel("-- W")
        self._power_label.setStyleSheet("font-weight: 600;")
        info_grid.addWidget(self._power_label, 2, 1)
        
        layout.addLayout(info_grid)
    
    def _create_icon_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("color: #888;")
        return label
    
    def _update_status(self):
        try:
            backend = get_backend_manager()
            gpu_infos = backend.get_gpu_info()
            
            if gpu_infos:
                info = gpu_infos[0]
                self._gpu_name.setText(info.name)
                
                usage = info.memory_usage_percent
                self._mem_bar.setValue(int(usage))
                self._mem_percent.setText(f"{usage:.1f}%")
                self._mem_text.setText(f"{format_memory(info.used_memory)} / {format_memory(info.total_memory)}")
                
                # 根据使用率改变颜色
                if usage > 90:
                    color = "#ef4444"
                elif usage > 70:
                    color = "#f59e0b"
                else:
                    color = "#10b981"
                
                self._mem_bar.setStyleSheet(f"""
                    QProgressBar::chunk {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:1 {color}88);
                        border-radius: 5px;
                    }}
                """)
                
                self._temp_label.setText(f"{info.temperature} °C")
                self._util_label.setText(f"{info.utilization} %")
                self._power_label.setText(f"{info.power_usage:.1f} W")
            else:
                self._gpu_name.setText("No GPU Detected")
        except Exception as e:
            logger.error(f"GPU status update failed: {e}")


class ModelPanel(StyledCard):
    """模型选择面板"""
    
    model_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_models()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("Model Selection")
        title.setStyleSheet("color: #7c8aff; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        # 模型下拉框
        self._model_combo = QComboBox()
        self._model_combo.setMinimumHeight(40)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self._model_combo)
        
        # 模型信息
        self._model_info = QLabel("Select a model to start")
        self._model_info.setWordWrap(True)
        self._model_info.setStyleSheet("color: #888; font-size: 12px; padding: 8px;")
        layout.addWidget(self._model_info)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self._load_btn = QPushButton("Load Model")
        self._load_btn.clicked.connect(self._load_model)
        btn_layout.addWidget(self._load_btn)
        
        self._unload_btn = QPushButton("Unload")
        self._unload_btn.setObjectName("secondaryBtn")
        self._unload_btn.clicked.connect(self._unload_model)
        self._unload_btn.setEnabled(False)
        btn_layout.addWidget(self._unload_btn)
        
        layout.addLayout(btn_layout)
        
        self._download_btn = QPushButton("Download Model")
        self._download_btn.setObjectName("secondaryBtn")
        self._download_btn.clicked.connect(self._download_model)
        layout.addWidget(self._download_btn)
    
    def _load_models(self):
        try:
            backend = get_backend_manager()
            available = backend.get_available_models()
            downloaded = backend.get_downloaded_models()
            
            self._model_combo.clear()
            for model_id, info in available.items():
                status = "[Ready]" if model_id in downloaded else "[Download]"
                self._model_combo.addItem(f"{status} {info.description}", model_id)
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
    
    def _on_model_changed(self, text):
        model_id = self._model_combo.currentData()
        if model_id:
            backend = get_backend_manager()
            info = backend.get_available_models().get(model_id)
            if info:
                self._model_info.setText(
                    f"Type: {info.task_type} | Resolution: {info.resolution}\n"
                    f"VRAM: {info.vram_required} GB | License: {info.license}"
                )
            self.model_changed.emit(model_id)
    
    def _load_model(self):
        model_id = self._model_combo.currentData()
        if not model_id:
            return
        
        self._load_btn.setEnabled(False)
        self._load_btn.setText("Loading...")
        
        try:
            backend = get_backend_manager()
            if backend.load_model(model_id):
                self._load_btn.setText("Loaded")
                self._unload_btn.setEnabled(True)
                QMessageBox.information(self, "Success", "Model loaded successfully")
            else:
                self._load_btn.setText("Load Model")
                QMessageBox.warning(self, "Failed", "Failed to load model")
        except Exception as e:
            self._load_btn.setText("Load Model")
            QMessageBox.critical(self, "Error", f"Load failed: {e}")
        
        self._load_btn.setEnabled(True)
    
    def _unload_model(self):
        try:
            backend = get_backend_manager()
            backend.unload_model()
            self._load_btn.setText("Load Model")
            self._unload_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unload failed: {e}")
    
    def _download_model(self):
        model_id = self._model_combo.currentData()
        if not model_id:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Download",
            f"Download model {model_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                backend = get_backend_manager()
                if backend.download_model(model_id):
                    QMessageBox.information(self, "Started", "Download started")
                else:
                    QMessageBox.warning(self, "Failed", "Failed to start download")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Download failed: {e}")
    
    def get_selected_model(self) -> str:
        return self._model_combo.currentData() or ""


class PromptPanel(StyledCard):
    """Prompt输入面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Prompt
        prompt_label = QLabel("Prompt")
        prompt_label.setStyleSheet("color: #7c8aff; font-weight: 600; font-size: 14px;")
        layout.addWidget(prompt_label)
        
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setPlaceholderText("Describe the video you want to generate...")
        self._prompt_edit.setMaximumHeight(100)
        layout.addWidget(self._prompt_edit)
        
        # 历史Prompt
        history_layout = QHBoxLayout()
        self._history_combo = QComboBox()
        self._history_combo.addItem("Prompt History")
        self._history_combo.currentTextChanged.connect(self._on_history_selected)
        history_layout.addWidget(self._history_combo)
        
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setObjectName("secondaryBtn")
        self._refresh_btn.setMaximumWidth(80)
        self._refresh_btn.clicked.connect(self._load_history)
        history_layout.addWidget(self._refresh_btn)
        layout.addLayout(history_layout)
        
        # Negative Prompt
        neg_label = QLabel("Negative Prompt")
        neg_label.setStyleSheet("color: #f87171; font-weight: 600; font-size: 14px;")
        layout.addWidget(neg_label)
        
        self._neg_prompt_edit = QTextEdit()
        self._neg_prompt_edit.setPlaceholderText("What to avoid in the video (optional)...")
        self._neg_prompt_edit.setMaximumHeight(70)
        layout.addWidget(self._neg_prompt_edit)
        
        self._load_history()
    
    def _load_history(self):
        try:
            backend = get_backend_manager()
            prompts = backend.get_prompt_history(limit=20)
            
            self._history_combo.clear()
            self._history_combo.addItem("Prompt History")
            for p in prompts:
                text = p["prompt"][:40] + "..." if len(p["prompt"]) > 40 else p["prompt"]
                self._history_combo.addItem(text, p["prompt"])
        except Exception as e:
            logger.error(f"Failed to load prompt history: {e}")
    
    def _on_history_selected(self, text):
        if text != "Prompt History":
            prompt = self._history_combo.currentData()
            if prompt:
                self._prompt_edit.setPlainText(prompt)
    
    def get_prompt(self) -> str:
        return self._prompt_edit.toPlainText().strip()
    
    def get_negative_prompt(self) -> str:
        return self._neg_prompt_edit.toPlainText().strip()


class ParametersPanel(StyledCard):
    """参数设置面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("Generation Parameters")
        title.setStyleSheet("color: #7c8aff; font-weight: 600; font-size: 14px;")
        layout.addWidget(title)
        
        # 分辨率
        res_group = QGroupBox("Resolution")
        res_layout = QGridLayout(res_group)
        res_layout.setSpacing(8)
        
        res_layout.addWidget(QLabel("Width:"), 0, 0)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(256, 1920)
        self._width_spin.setValue(832)
        self._width_spin.setSingleStep(64)
        res_layout.addWidget(self._width_spin, 0, 1)
        
        res_layout.addWidget(QLabel("Height:"), 1, 0)
        self._height_spin = QSpinBox()
        self._height_spin.setRange(256, 1080)
        self._height_spin.setValue(480)
        self._height_spin.setSingleStep(64)
        res_layout.addWidget(self._height_spin, 1, 1)
        
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(["480P (832x480)", "720P (1280x720)", "Custom"])
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        res_layout.addWidget(QLabel("Preset:"), 2, 0)
        res_layout.addWidget(self._preset_combo, 2, 1)
        
        layout.addWidget(res_group)
        
        # 视频参数
        video_group = QGroupBox("Video Settings")
        video_layout = QGridLayout(video_group)
        video_layout.setSpacing(8)
        
        video_layout.addWidget(QLabel("Frames:"), 0, 0)
        self._frames_spin = QSpinBox()
        self._frames_spin.setRange(1, 200)
        self._frames_spin.setValue(81)
        video_layout.addWidget(self._frames_spin, 0, 1)
        
        video_layout.addWidget(QLabel("FPS:"), 1, 0)
        self._fps_spin = QSpinBox()
        self._fps_spin.setRange(1, 30)
        self._fps_spin.setValue(16)
        video_layout.addWidget(self._fps_spin, 1, 1)
        
        video_layout.addWidget(QLabel("Duration:"), 2, 0)
        self._duration_label = QLabel("5.1 sec")
        self._duration_label.setStyleSheet("color: #7c8aff; font-weight: 600;")
        video_layout.addWidget(self._duration_label, 2, 1)
        
        self._frames_spin.valueChanged.connect(self._update_duration)
        self._fps_spin.valueChanged.connect(self._update_duration)
        
        layout.addWidget(video_group)
        
        # 生成参数
        gen_group = QGroupBox("Generation Settings")
        gen_layout = QGridLayout(gen_group)
        gen_layout.setSpacing(8)
        
        gen_layout.addWidget(QLabel("Steps:"), 0, 0)
        self._steps_spin = QSpinBox()
        self._steps_spin.setRange(1, 100)
        self._steps_spin.setValue(50)
        gen_layout.addWidget(self._steps_spin, 0, 1)
        
        gen_layout.addWidget(QLabel("CFG Scale:"), 1, 0)
        self._cfg_spin = QDoubleSpinBox()
        self._cfg_spin.setRange(1.0, 20.0)
        self._cfg_spin.setValue(5.0)
        self._cfg_spin.setSingleStep(0.5)
        gen_layout.addWidget(self._cfg_spin, 1, 1)
        
        gen_layout.addWidget(QLabel("Seed:"), 2, 0)
        seed_layout = QHBoxLayout()
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(-1, 2147483647)
        self._seed_spin.setValue(-1)
        seed_layout.addWidget(self._seed_spin)
        self._random_btn = QPushButton("Random")
        self._random_btn.setObjectName("secondaryBtn")
        self._random_btn.setMaximumWidth(70)
        self._random_btn.clicked.connect(self._random_seed)
        seed_layout.addWidget(self._random_btn)
        gen_layout.addLayout(seed_layout, 2, 1)
        
        layout.addWidget(gen_group)
        
        # 优化选项
        opt_group = QGroupBox("Optimization")
        opt_layout = QVBoxLayout(opt_group)
        opt_layout.setSpacing(8)
        
        self._cpu_offload = QCheckBox("CPU Offload (Low VRAM)")
        opt_layout.addWidget(self._cpu_offload)
        
        self._vae_tiling = QCheckBox("VAE Tiling")
        self._vae_tiling.setChecked(True)
        opt_layout.addWidget(self._vae_tiling)
        
        self._flash_attn = QCheckBox("Flash Attention")
        self._flash_attn.setChecked(True)
        opt_layout.addWidget(self._flash_attn)
        
        layout.addWidget(opt_group)
    
    def _on_preset_changed(self, text):
        if "480P" in text:
            self._width_spin.setValue(832)
            self._height_spin.setValue(480)
        elif "720P" in text:
            self._width_spin.setValue(1280)
            self._height_spin.setValue(720)
    
    def _update_duration(self):
        frames = self._frames_spin.value()
        fps = self._fps_spin.value()
        if fps > 0:
            duration = frames / fps
            self._duration_label.setText(f"{duration:.1f} sec")
    
    def _random_seed(self):
        import random
        self._seed_spin.setValue(random.randint(0, 2147483647))
    
    def get_params(self) -> Dict[str, Any]:
        return {
            "width": self._width_spin.value(),
            "height": self._height_spin.value(),
            "num_frames": self._frames_spin.value(),
            "fps": self._fps_spin.value(),
            "steps": self._steps_spin.value(),
            "cfg_scale": self._cfg_spin.value(),
            "seed": self._seed_spin.value(),
            "cpu_offload": self._cpu_offload.isChecked(),
            "vae_tiling": self._vae_tiling.isChecked(),
            "flash_attention": self._flash_attn.isChecked()
        }


class TaskListPanel(StyledCard):
    """任务列表面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_tasks)
        self._update_timer.start(1000)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 标题和按钮
        header = QHBoxLayout()
        title = QLabel("Task Queue")
        title.setStyleSheet("color: #7c8aff; font-weight: 600; font-size: 14px;")
        header.addWidget(title)
        
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("secondaryBtn")
        self._clear_btn.setMaximumWidth(60)
        self._clear_btn.clicked.connect(self._clear_completed)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)
        
        # 任务列表
        self._task_list = QListWidget()
        layout.addWidget(self._task_list)
        
        # 状态标签
        self._status_label = QLabel("Queue: 0 pending | 0 running | 0 completed")
        self._status_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self._status_label)
    
    def _update_tasks(self):
        try:
            backend = get_backend_manager()
            queue = backend.get_task_queue()
            status = queue.get_queue_status()
            
            self._status_label.setText(
                f"Queue: {status['pending']} pending | {status['running']} running | {status['completed']} completed"
            )
            
            tasks = queue.get_all_tasks()
            if self._task_list.count() != len(tasks):
                self._task_list.clear()
                for task in tasks:
                    icons = {
                        TaskStatus.PENDING: "WAIT",
                        TaskStatus.RUNNING: "RUN",
                        TaskStatus.COMPLETED: "DONE",
                        TaskStatus.FAILED: "FAIL",
                        TaskStatus.CANCELLED: "STOP"
                    }
                    icon = icons.get(task.status, "???")
                    progress = f" [{task.progress:.0f}%]" if task.status == TaskStatus.RUNNING else ""
                    self._task_list.addItem(f"[{icon}] {task.task_id}: {task.prompt[:25]}...{progress}")
        except Exception as e:
            logger.error(f"Failed to update tasks: {e}")
    
    def _clear_completed(self):
        try:
            backend = get_backend_manager()
            backend.get_task_queue().clear_completed()
        except Exception as e:
            logger.error(f"Failed to clear tasks: {e}")


class LogPanel(StyledCard):
    """日志面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._log_lines = []
        self._max_lines = 500
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        header = QHBoxLayout()
        title = QLabel("Log Output")
        title.setStyleSheet("color: #7c8aff; font-weight: 600; font-size: 14px;")
        header.addWidget(title)
        
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("secondaryBtn")
        self._clear_btn.setMaximumWidth(60)
        self._clear_btn.clicked.connect(self._clear_log)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 11))
        self._log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a1a;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        layout.addWidget(self._log_text)
    
    def add_log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "DEBUG": "#6b7280",
            "INFO": "#e0e0e0",
            "WARNING": "#fbbf24",
            "ERROR": "#ef4444",
            "CRITICAL": "#dc2626"
        }
        color = colors.get(level, "#e0e0e0")
        
        html = f'<span style="color: #6b7280;">[{timestamp}]</span> <span style="color: {color}; font-weight: 600;">[{level}]</span> <span style="color: {color};">{message}</span>'
        self._log_lines.append(html)
        
        if len(self._log_lines) > self._max_lines:
            self._log_lines = self._log_lines[-self._max_lines:]
        
        self._log_text.setHtml("<br>".join(self._log_lines))
        self._log_text.verticalScrollBar().setValue(
            self._log_text.verticalScrollBar().maximum()
        )
    
    def _clear_log(self):
        self._log_lines.clear()
        self._log_text.clear()


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self._backend = get_backend_manager()
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        logger.info("Main window initialized")
    
    def _setup_ui(self):
        self.setWindowTitle("VideoGenAI - Local AI Video Generation")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # 应用主题
        self.setStyleSheet(MODERN_DARK_THEME)
        
        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)
        
        # 主布局
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # ===== 左侧面板 =====
        left_panel = QWidget()
        left_panel.setMaximumWidth(420)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        # Logo
        logo_label = QLabel("VideoGenAI")
        logo_label.setObjectName("titleLabel")
        logo_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(logo_label)
        
        # GPU状态
        self._gpu_status = GPUStatusCard()
        left_layout.addWidget(self._gpu_status)
        
        # 模型选择
        self._model_panel = ModelPanel()
        left_layout.addWidget(self._model_panel)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(12)
        
        # Prompt
        self._prompt_panel = PromptPanel()
        scroll_layout.addWidget(self._prompt_panel)
        
        # 参数
        self._params_panel = ParametersPanel()
        scroll_layout.addWidget(self._params_panel)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # 生成按钮
        self._generate_btn = QPushButton("Generate Video")
        self._generate_btn.setObjectName("generateBtn")
        self._generate_btn.clicked.connect(self._generate)
        left_layout.addWidget(self._generate_btn)
        
        self._stop_btn = QPushButton("Stop Generation")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_generation)
        left_layout.addWidget(self._stop_btn)
        
        self._output_btn = QPushButton("Open Output Folder")
        self._output_btn.setObjectName("secondaryBtn")
        self._output_btn.clicked.connect(self._open_output_dir)
        left_layout.addWidget(self._output_btn)
        
        main_layout.addWidget(left_panel)
        
        # ===== 右侧面板 =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        # 标签页
        self._tab_widget = QTabWidget()
        
        # 任务列表
        self._task_panel = TaskListPanel()
        self._tab_widget.addTab(self._task_panel, "Tasks")
        
        # 日志
        self._log_panel = LogPanel()
        self._tab_widget.addTab(self._log_panel, "Logs")
        
        # 历史
        self._history_widget = self._create_history_panel()
        self._tab_widget.addTab(self._history_widget, "History")
        
        right_layout.addWidget(self._tab_widget)
        
        # 进度区域
        progress_frame = StyledCard()
        progress_layout = QVBoxLayout(progress_frame)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumHeight(20)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setVisible(False)
        progress_layout.addWidget(self._progress_bar)
        
        self._progress_label = QLabel("")
        self._progress_label.setAlignment(Qt.AlignCenter)
        self._progress_label.setVisible(False)
        progress_layout.addWidget(self._progress_label)
        
        right_layout.addWidget(progress_frame)
        
        main_layout.addWidget(right_panel)
    
    def _create_history_panel(self) -> QWidget:
        panel = StyledCard()
        layout = QVBoxLayout(panel)
        
        self._history_list = QListWidget()
        layout.addWidget(self._history_list)
        
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self._load_history)
        btn_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self._clear_history)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        
        self._load_history()
        return panel
    
    def _setup_menu(self):
        menubar = self.menuBar()
        
        # File
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Open Output Folder", self._open_output_dir)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        
        # Model
        model_menu = menubar.addMenu("Model")
        model_menu.addAction("Load Model", self._model_panel._load_model)
        model_menu.addAction("Unload Model", self._model_panel._unload_model)
        model_menu.addSeparator()
        model_menu.addAction("Download Model", self._model_panel._download_model)
        
        # Tools
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Clear Cache", self._clear_cache)
        
        # Help
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self._show_about)
    
    def _setup_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")
    
    def _generate(self):
        prompt = self._prompt_panel.get_prompt()
        if not prompt:
            QMessageBox.warning(self, "Warning", "Please enter a prompt")
            return
        
        negative_prompt = self._prompt_panel.get_negative_prompt()
        params = self._params_panel.get_params()
        model_id = self._model_panel.get_selected_model()
        
        self._generate_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress_bar.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress_bar.setValue(0)
        self._progress_label.setText("Generating...")
        self._progress_label.setStyleSheet("color: #7c8aff; font-weight: 600;")
        
        try:
            task_id = self._backend.submit_task(
                task_type=TaskType.TEXT_TO_VIDEO,
                prompt=prompt,
                negative_prompt=negative_prompt,
                model_id=model_id,
                **params
            )
            
            self._status_bar.showMessage(f"Task submitted: {task_id}")
            self._log_panel.add_log(f"Task submitted: {task_id}", "INFO")
            
            self._current_task_id = task_id
            self._progress_timer = QTimer()
            self._progress_timer.timeout.connect(self._update_progress)
            self._progress_timer.start(500)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to submit task: {e}")
            self._reset_generation_ui()
    
    def _stop_generation(self):
        if hasattr(self, '_current_task_id'):
            self._backend.cancel_task(self._current_task_id)
            self._log_panel.add_log(f"Task cancelled: {self._current_task_id}", "WARNING")
        self._reset_generation_ui()
    
    def _update_progress(self):
        if not hasattr(self, '_current_task_id'):
            return
        
        status = self._backend.get_task_status(self._current_task_id)
        if status:
            progress = status.get('progress', 0)
            self._progress_bar.setValue(int(progress))
            self._progress_label.setText(f"Progress: {progress:.1f}%")
            
            if status['status'] in ['completed', 'failed', 'cancelled']:
                self._progress_timer.stop()
                
                if status['status'] == 'completed':
                    self._progress_label.setText("Generation Complete!")
                    self._progress_label.setStyleSheet("color: #10b981; font-weight: 600;")
                    self._log_panel.add_log(f"Task completed: {self._current_task_id}", "INFO")
                elif status['status'] == 'failed':
                    self._progress_label.setText(f"Failed: {status.get('error_message', 'Unknown error')}")
                    self._progress_label.setStyleSheet("color: #ef4444; font-weight: 600;")
                    self._log_panel.add_log(f"Task failed: {status.get('error_message')}", "ERROR")
                
                QTimer.singleShot(3000, self._reset_generation_ui)
    
    def _reset_generation_ui(self):
        self._generate_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._progress_label.setVisible(False)
    
    def _open_output_dir(self):
        output_dir = Path("./outputs")
        output_dir.mkdir(exist_ok=True)
        os.startfile(str(output_dir))
    
    def _load_history(self):
        try:
            history = self._backend.get_history(limit=50)
            self._history_list.clear()
            for record in history:
                self._history_list.addItem(
                    f"[{record['created_at'][:16]}] {record['model_id']}: {record['prompt'][:35]}..."
                )
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
    
    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Confirm", "Clear all history?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._backend.get_history_manager().clear_history()
            self._history_list.clear()
    
    def _clear_cache(self):
        self._backend.clear_cache()
        self._status_bar.showMessage("Cache cleared")
    
    def _show_about(self):
        QMessageBox.about(
            self,
            "About VideoGenAI",
            "<h2>VideoGenAI v1.0.0</h2>"
            "<p>Local AI Video Generation Software</p>"
            "<p>Based on Wan2.1 Open Source Model</p>"
            "<p>100% Local - No Internet Required</p>"
            "<p>License: Apache 2.0</p>"
        )
    
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Confirm Exit", "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._backend.shutdown()
            event.accept()
        else:
            event.ignore()
