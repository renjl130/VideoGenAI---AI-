"""Shared Qt style definitions for the VideoGenAI desktop UI."""

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

# Keep the historic name for integrations that import it directly.
ELEGANT_THEME = LIGHT_THEME
