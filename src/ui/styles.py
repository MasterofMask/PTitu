"""
Estilos CSS para la interfaz - Tema Oscuro Profesional
"""

MAIN_STYLE = """
/* ── Variables globales ─────────────────────────────────────────────────── */
* {
    font-family: 'Segoe UI', 'Calibri', sans-serif;
    font-size: 10pt;
}

/* ── Ventana principal ──────────────────────────────────────────────────── */
QMainWindow {
    background-color: #0f1117;
}

QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
}

/* ── Pestañas ────────────────────────────────────────────────────────────── */
QTabWidget {
    background-color: #0f1117;
}

QTabWidget::pane {
    border: none;
    border-top: 1px solid #1e2433;
    background-color: #141821;
    top: 0px;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar {
    background: #0f1117;
    border: none;
    border-bottom: 1px solid #1e2433;
}

QTabBar::tab {
    background: transparent;
    color: #64748b;
    padding: 10px 28px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 4px;
    min-width: 80px;
    font-size: 10pt;
}

QTabBar::tab:selected {
    background: transparent;
    color: #60a5fa;
    border-bottom: 2px solid #3b82f6;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    color: #94a3b8;
    border-bottom: 2px solid #334155;
}

/* ── Botones principales ─────────────────────────────────────────────────── */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2563eb, stop:1 #1e40af);
    color: #ffffff;
    border: none;
    padding: 8px 18px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 10pt;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3b82f6, stop:1 #2563eb);
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1e40af, stop:1 #1e3a8a);
}

QPushButton:disabled {
    background: #1e2433;
    color: #4b5563;
    border: 1px solid #2d3748;
}

/* Botón de peligro (rojo) - se aplica vía setStyleSheet individual */
QPushButton[danger="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #dc2626, stop:1 #991b1b);
}

/* ── Etiquetas ───────────────────────────────────────────────────────────── */
QLabel {
    color: #e2e8f0;
    background: transparent;
}

/* ── Grupos ──────────────────────────────────────────────────────────────── */
QGroupBox {
    font-weight: bold;
    font-size: 9pt;
    color: #94a3b8;
    border: 1px solid #2d3748;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    background: #141821;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #64748b;
}

/* ── Listas ──────────────────────────────────────────────────────────────── */
QListWidget {
    background-color: #141821;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 4px;
    color: #e2e8f0;
    outline: none;
}

QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
    margin: 1px 2px;
    color: #cbd5e1;
}

QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1d4ed8, stop:1 #2563eb);
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background-color: #1e2433;
    color: #e2e8f0;
}

/* ── Barra de estado ─────────────────────────────────────────────────────── */
QStatusBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0f1117, stop:1 #141821);
    color: #64748b;
    border-top: 1px solid #1e2433;
    font-size: 9pt;
}

/* ── Barra de progreso ───────────────────────────────────────────────────── */
QProgressBar {
    border: 1px solid #2d3748;
    border-radius: 5px;
    background-color: #141821;
    text-align: center;
    color: #94a3b8;
    height: 14px;
    font-size: 8pt;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2563eb, stop:1 #7c3aed);
    border-radius: 4px;
}

/* ── Menú ────────────────────────────────────────────────────────────────── */
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #161b27, stop:1 #0f1117);
    color: #94a3b8;
    border-bottom: 1px solid #1e2433;
    padding: 2px;
}

QMenuBar::item {
    padding: 5px 12px;
    border-radius: 4px;
    background: transparent;
}

QMenuBar::item:selected {
    background: #1e2433;
    color: #e2e8f0;
}

QMenu {
    background-color: #1a2035;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 4px;
    color: #e2e8f0;
}

QMenu::item {
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1d4ed8, stop:1 #2563eb);
    color: white;
}

QMenu::separator {
    height: 1px;
    background: #2d3748;
    margin: 4px 8px;
}

/* ── Scroll ──────────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0f1117;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0f1117;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #475569;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
QLineEdit {
    background-color: #1a2035;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e2e8f0;
    selection-background-color: #2563eb;
}

QLineEdit:focus {
    border-color: #3b82f6;
    background-color: #1e2845;
}

QComboBox {
    background-color: #1a2035;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e2e8f0;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #64748b;
    width: 0;
    height: 0;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #1a2035;
    border: 1px solid #2d3748;
    border-radius: 6px;
    color: #e2e8f0;
    selection-background-color: #2563eb;
}

/* ── Diálogos ────────────────────────────────────────────────────────────── */
QDialog {
    background-color: #0f1117;
    color: #e2e8f0;
}

QMessageBox {
    background-color: #141821;
    color: #e2e8f0;
}

QMessageBox QLabel {
    color: #e2e8f0;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 6px 16px;
}

/* ── Frames ──────────────────────────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #2d3748;
}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter::handle {
    background: #2d3748;
}

/* ── Checkbox ────────────────────────────────────────────────────────────── */
QCheckBox {
    color: #cbd5e1;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #4b5563;
    border-radius: 4px;
    background: #1a2035;
}

QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2563eb, stop:1 #7c3aed);
    border-color: #3b82f6;
}

QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

/* ── Input Dialog ────────────────────────────────────────────────────────── */
QInputDialog {
    background-color: #141821;
}

QInputDialog QLabel {
    color: #e2e8f0;
}

QInputDialog QLineEdit {
    background-color: #1a2035;
    border: 1px solid #2d3748;
    color: #e2e8f0;
}
"""


# Estilo específico para botones grandes de la pantalla de inicio
HOME_BUTTON_STYLE = """
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {color1}, stop:1 {color2});
    color: rgba(255,255,255,0.95);
    border: none;
    border-radius: 12px;
    font-size: 13pt;
    font-weight: 700;
    text-align: left;
    padding: 20px 24px;
    line-height: 1.6;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {hover1}, stop:1 {hover2});
    color: white;
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {color2}, stop:1 {color1});
}}
"""

BUTTON_COLORS = {
    'blue':   ('#2563eb', '#1d4ed8', '#3b82f6', '#2563eb'),
    'purple': ('#7c3aed', '#6d28d9', '#8b5cf6', '#7c3aed'),
    'teal':   ('#0d9488', '#0f766e', '#14b8a6', '#0d9488'),
    'amber':  ('#d97706', '#b45309', '#f59e0b', '#d97706'),
    'rose':   ('#e11d48', '#be123c', '#f43f5e', '#e11d48'),
    'indigo': ('#4338ca', '#3730a3', '#6366f1', '#4338ca'),
}


def get_home_button_style(color_name: str) -> str:
    """Retorna el estilo para un botón de inicio con el color especificado."""
    c = BUTTON_COLORS.get(color_name, BUTTON_COLORS['blue'])
    return HOME_BUTTON_STYLE.format(
        color1=c[0], color2=c[1], hover1=c[2], hover2=c[3]
    )