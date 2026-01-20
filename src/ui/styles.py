"""
Estilos CSS para la interfaz
"""

MAIN_STYLE = """
QMainWindow {
    background-color: #f5f5f5;
}

QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}

QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #106ebe;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}

QLabel {
    color: #333333;
}

QGroupBox {
    font-weight: bold;
    border: 2px solid #cccccc;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QListWidget {
    background-color: white;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #0078d4;
    color: white;
}

QListWidget::item:hover {
    background-color: #e5f3ff;
}

QStatusBar {
    background-color: #f0f0f0;
    color: #333333;
}

QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}
"""