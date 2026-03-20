"""
Ventana principal de la aplicación — Tema Oscuro Profesional
"""
import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTabWidget,
    QStatusBar, QAction, QMenuBar, QMessageBox,
    QProgressBar, QListWidget, QListWidgetItem,
    QGridLayout, QGroupBox, QScrollArea, QInputDialog,
    QDialog, QComboBox, QLineEdit, QFrame, QCheckBox,
    QAbstractItemView, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon, QImage, QPixmap, QColor, QPainter, QBrush, QLinearGradient

from PIL import Image
import numpy as np

from src.core.database import DatabaseManager
from src.ui.styles import MAIN_STYLE, get_home_button_style

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Sistema de iconos desde archivos SVG locales
#  Carpeta: src/ui/icons/  (archivos Feather Icons descargados)
# ─────────────────────────────────────────────────────────────────────────────

# Directorio de iconos relativo a este archivo
_ICONS_DIR = Path(__file__).parent / "icons"

# Mapeo nombre → archivo SVG de Feather Icons
_ICON_FILES = {
    'import':  'download-cloud.svg',
    'gallery': 'image.svg',
    'persons': 'users.svg',
    'export':  'upload-cloud.svg',
    'trash':   'trash-2.svg',
    'tag':     'tag.svg',
    'edit':    'edit-2.svg',
    'eye':     'eye.svg',
    'refresh': 'refresh-cw.svg',
    'search':  'search.svg',
    'home':    'home.svg',
    'filter':  'filter.svg',
    'cluster': 'share-2.svg',
}

# Cache de iconos ya cargados
_icon_cache: dict = {}


def get_icon(name: str, size: int = 20, color: str = "#94a3b8") -> QIcon:
    """
    Carga un icono SVG desde disco, lo colorea y lo retorna como QIcon.
    Usa caché para no releer el archivo en cada llamada.
    Requiere PyQt5.QtSvg (módulo opcional). Si no está disponible, retorna QIcon vacío.
    """
    cache_key = f"{name}_{size}_{color}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    svg_file = _ICONS_DIR / _ICON_FILES.get(name, 'image.svg')
    if not svg_file.exists():
        return QIcon()

    try:
        # Leer SVG y reemplazar color del stroke
        svg_text = svg_file.read_text(encoding="utf-8")
        # Feather Icons usan currentColor — reemplazamos con el color deseado
        svg_text = svg_text.replace('currentColor', color)
        # Asegurar que tenga stroke explícito si no tiene
        if 'stroke=' not in svg_text:
            svg_text = svg_text.replace('<svg ', f'<svg stroke="{color}" ')

        from PyQt5.QtSvg import QSvgRenderer
        from PyQt5.QtCore import QByteArray
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon = QIcon(pixmap)
        _icon_cache[cache_key] = icon
        return icon
    except Exception:
        return QIcon()


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo de etiquetado de rostros
# ─────────────────────────────────────────────────────────────────────────────

class FaceLabelingDialog(QDialog):
    """Diálogo para etiquetar cada rostro detectado. Soporta multi-rostro."""

    def __init__(self, photo_id: int, db, parent=None):
        super().__init__(parent)
        self.photo_id = photo_id
        self.db = db
        self.face_widgets = []

        photo = db.get_photo_by_id(photo_id)
        self.photo_path = Path(photo['file_path']) if photo else None

        self.setWindowTitle(f"Etiquetar rostros — {photo['file_name'] if photo else ''}")
        self.setMinimumWidth(520)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background-color: #0f1117; color: #e2e8f0; }
            QLabel  { color: #e2e8f0; background: transparent; }
            QFrame  { background: #1a2035; border-radius: 8px; }
            QScrollArea { border: none; background: transparent; }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Asigna un nombre a cada rostro detectado:")
        title.setStyleSheet("font-weight: bold; font-size: 11pt; color: #e2e8f0;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(280)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.faces_layout = QVBoxLayout(container)
        self.faces_layout.setSpacing(10)

        faces = self.db.get_faces_by_photo(self.photo_id)
        all_persons = self.db.get_all_persons()

        if not faces:
            self.faces_layout.addWidget(QLabel("No se detectaron rostros en esta fotografía."))
        else:
            for idx, face in enumerate(faces):
                self.faces_layout.addWidget(self._build_face_row(idx, face, all_persons))

        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Guardar etiquetas")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton { background: #1e2433; color: #94a3b8;
                          border: 1px solid #2d3748; border-radius: 6px;
                          padding: 8px 18px; }
            QPushButton:hover { background: #253047; color: #e2e8f0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _build_face_row(self, idx: int, face: dict, all_persons: list):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { background: #1a2035; border: 1px solid #2d3748;
                     border-radius: 8px; padding: 6px; }
        """)
        row = QHBoxLayout(frame)
        row.setSpacing(12)

        thumb_label = QLabel()
        thumb_label.setFixedSize(72, 72)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setStyleSheet("""
            border: 2px solid #2d3748; border-radius: 36px;
            background: #0f1117;
        """)

        if self.photo_path and self.photo_path.exists():
            try:
                img = Image.open(self.photo_path).convert("RGB")
                x, y, w, h = face['bbox_x'], face['bbox_y'], face['bbox_width'], face['bbox_height']
                mx, my = int(w * 0.2), int(h * 0.2)
                x1, y1 = max(0, x - mx), max(0, y - my)
                x2, y2 = min(img.width, x + w + mx), min(img.height, y + h + my)
                crop = img.crop((x1, y1, x2, y2)).resize((72, 72), Image.BILINEAR)
                arr = np.array(crop)
                h_c, w_c, ch = arr.shape
                qimg = QImage(arr.data, w_c, h_c, ch * w_c, QImage.Format_RGB888)
                thumb_label.setPixmap(QPixmap.fromImage(qimg))
            except Exception:
                thumb_label.setText("?")

        row.addWidget(thumb_label)

        info_col = QVBoxLayout()
        conf_label = QLabel(f"Rostro #{idx + 1}   confianza: {face['confidence']:.0%}")
        conf_label.setStyleSheet("color: #64748b; font-size: 9pt;")
        info_col.addWidget(conf_label)

        current_name = ""
        if face.get('person_id'):
            p = self.db.get_person_by_id(face['person_id'])
            if p:
                current_name = p['name'] or f"Persona {p['cluster_id']}"

        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("")
        for p in all_persons:
            if p.get('name'):
                combo.addItem(p['name'], userData=p['id'])

        if current_name:
            idx_combo = combo.findText(current_name)
            if idx_combo >= 0:
                combo.setCurrentIndex(idx_combo)
            else:
                combo.setCurrentText(current_name)

        combo.setPlaceholderText("Escribe o selecciona un nombre…")
        combo.lineEdit().setMaxLength(50)
        info_col.addWidget(QLabel("Nombre:"))
        info_col.addWidget(combo)

        row.addLayout(info_col)
        row.setStretch(1, 1)
        self.face_widgets.append((face['id'], combo))
        return frame

    def _save(self):
        saved = 0
        for face_id, combo in self.face_widgets:
            name = combo.currentText().strip()
            if not name:
                continue
            existing = next((p for p in self.db.get_all_persons() if p.get('name') == name), None)
            if existing:
                person_id = existing['id']
            else:
                person_id = self.db.insert_person(cluster_id=self._next_cluster_id(), name=name)
            self.db.update_face_person(face_id, person_id)
            saved += 1

        if saved:
            QMessageBox.information(self, "Guardado", f"✓ {saved} etiqueta(s) guardada(s).")
            self.accept()
        else:
            self.reject()

    def _next_cluster_id(self) -> int:
        persons = self.db.get_all_persons()
        if not persons:
            return 9000
        max_id = 9000
        for p in persons:
            try:
                cid = p['cluster_id']
                if isinstance(cid, (bytes, bytearray)):
                    cid = int.from_bytes(cid[:4], 'little')
                val = int(cid)
                if val > max_id:
                    max_id = val
            except (TypeError, ValueError):
                pass
        return max_id + 1


# ─────────────────────────────────────────────────────────────────────────────
#  Ventana principal
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
        self.load_statistics()

    def init_ui(self):
        self.setWindowTitle("PTitu — Organizador de Fotografías")
        self.setGeometry(80, 60, 1280, 820)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(MAIN_STYLE)

        # Icono de ventana y barra de tareas
        icon_path = Path(__file__).parent / "icons" / "ptitu.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.create_menu_bar()
        self._create_header(main_layout)

        # Pestañas
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._create_home_tab(),    get_icon("home",    18), "  Inicio  ")
        self.tabs.addTab(self._create_gallery_tab(), get_icon("gallery", 18), "  Galería  ")
        self.tabs.addTab(self._create_persons_tab(), get_icon("persons", 18), "  Personas  ")
        main_layout.addWidget(self.tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(220)
        self.progress_bar.setMaximumHeight(12)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _create_header(self, parent_layout):
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0f1117, stop:0.4 #161b27, stop:1 #0f1117);
                border-bottom: 1px solid #1e2433;
            }
        """)
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        title = QLabel("PTitu")
        title.setStyleSheet("""
            font-size: 20pt;
            font-weight: 800;
            background: transparent;
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #60a5fa, stop:1 #a78bfa);
        """)
        # PyQt5 no soporta gradient en color directamente, usamos HTML
        title.setText('<span style="color:#60a5fa; font-size:20pt; font-weight:800;">P</span>'
                      '<span style="color:#818cf8; font-size:20pt; font-weight:800;">Titu</span>')
        title.setTextFormat(Qt.RichText)
        hl.addWidget(title)

        subtitle = QLabel("Organizador de Fotografías")
        subtitle.setStyleSheet("color: #475569; font-size: 9pt; background: transparent;")
        hl.addWidget(subtitle)
        hl.addStretch()

        # Panel de estadísticas compacto
        for icon_label, attr_name, display in [
            ("Fotos", "stats_photos", "0"),
            ("Rostros", "stats_faces", "0"),
            ("Personas", "stats_persons", "0"),
        ]:
            stat_widget = QWidget()
            stat_widget.setStyleSheet("""
                QWidget { background: #141821; border: 1px solid #1e2433;
                          border-radius: 8px; }
            """)
            stat_widget.setFixedSize(88, 44)
            sv = QVBoxLayout(stat_widget)
            sv.setContentsMargins(8, 4, 8, 4)
            sv.setSpacing(0)

            val_label = QLabel(display)
            val_label.setAlignment(Qt.AlignCenter)
            val_label.setStyleSheet("font-size: 14pt; font-weight: 700; color: #60a5fa; background: transparent; border: none;")
            setattr(self, attr_name, val_label)

            lbl = QLabel(icon_label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size: 7pt; color: #64748b; background: transparent; border: none;")

            sv.addWidget(val_label)
            sv.addWidget(lbl)
            hl.addWidget(stat_widget)
            hl.addSpacing(6)

        parent_layout.addWidget(header)

    # ── Menú ──────────────────────────────────────────────────────────────────

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Archivo")
        self._add_action(file_menu, "Importar fotos...", self.import_photos)
        file_menu.addSeparator()
        self._add_action(file_menu, "Salir", self.close)

        tools_menu = menubar.addMenu("Herramientas")
        self._add_action(tools_menu, "Limpiar duplicados", self.clean_duplicates)
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Eliminar fotos seleccionadas...", self.delete_selected_photos)
        self._add_action(tools_menu, "Eliminar TODAS las fotos", self.delete_all_photos)
        tools_menu.addSeparator()
        self._add_action(tools_menu, "Gestionar etiquetas de personas...", self.delete_person_label)

        help_menu = menubar.addMenu("Ayuda")
        self._add_action(help_menu, "Acerca de", self.show_about)

    def _add_action(self, menu, text, slot):
        action = QAction(text, self)
        action.triggered.connect(slot)
        menu.addAction(action)

    # ── Pestaña Inicio ────────────────────────────────────────────────────────

    def _create_home_tab(self):
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Título de sección
        sec = QLabel("¿Qué deseas hacer?")
        sec.setStyleSheet("color: #64748b; font-size: 10pt; font-weight: 600;")
        outer.addWidget(sec)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Configuración de botones: (título, descripción, color, acción, fila, col)
        buttons = [
            ("Importar Fotos",       "Agrega nuevas fotos a tu colección",       'blue',   self.import_photos,              0, 0),
            ("Ver Galería",          "Explora y filtra tus fotografías",          'purple', lambda: self.tabs.setCurrentIndex(1), 0, 1),
            ("Personas",             "Gestiona y etiqueta personas detectadas",   'teal',   lambda: self.tabs.setCurrentIndex(2), 1, 0),
            ("Exportar por Escena",  "Copia tus fotos organizadas por categoría", 'indigo', self.export_by_scene,             1, 1),
        ]

        for title_txt, desc_txt, color, slot, r, c in buttons:
            btn = QPushButton()
            btn.setMinimumHeight(96)
            btn.setText(title_txt + "\n" + desc_txt)
            btn.setStyleSheet(get_home_button_style(color))
            btn.clicked.connect(slot)
            grid.addWidget(btn, r, c)

        outer.addLayout(grid)
        outer.addStretch()
        return widget

    # ── Pestaña Galería ───────────────────────────────────────────────────────

    def _create_gallery_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Barra de filtros
        filter_bar = QWidget()
        filter_bar.setStyleSheet("QWidget { background: #141821; border-radius: 8px; }")
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(12, 8, 12, 8)

        fl.addWidget(QLabel("Filtrar:"))
        self.scene_filter = QComboBox()
        self.scene_filter.addItem("Todas las categorías", None)
        for cat, label in [
            ("interiores", "Interiores"),
            ("exteriores", "Exteriores"),
            ("restaurantes", "Restaurantes"),
            ("eventos_sociales", "Eventos Sociales"),
            ("actividades_deportivas", "Actividades Deportivas"),
        ]:
            self.scene_filter.addItem(label, cat)
        self.scene_filter.currentIndexChanged.connect(self.filter_gallery_by_scene)
        fl.addWidget(self.scene_filter)
        fl.addStretch()

        btn_refresh_g = QPushButton(get_icon("refresh", 15), "  Actualizar")
        btn_refresh_g.setFixedWidth(110)
        btn_refresh_g.clicked.connect(self.load_gallery)
        fl.addWidget(btn_refresh_g)

        btn_detail = QPushButton(get_icon("eye", 15), "  Ver detalle")
        btn_detail.setFixedWidth(110)
        btn_detail.clicked.connect(self.show_selected_photo_detail)
        fl.addWidget(btn_detail)

        layout.addWidget(filter_bar)

        # Lista de fotos
        self.photo_list = QListWidget()
        self.photo_list.setViewMode(QListWidget.IconMode)
        self.photo_list.setIconSize(QSize(180, 180))
        self.photo_list.setResizeMode(QListWidget.Adjust)
        self.photo_list.setSpacing(8)
        self.photo_list.setUniformItemSizes(True)
        self.photo_list.itemDoubleClicked.connect(self.show_photo_detail)
        layout.addWidget(self.photo_list)

        return widget

    # ── Pestaña Personas ──────────────────────────────────────────────────────

    def _create_persons_tab(self):
        # Reusar método existente que ya funciona bien
        return self.create_persons_tab()

    def create_persons_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Buscador
        search_bar = QWidget()
        search_bar.setStyleSheet("QWidget { background: #141821; border-radius: 8px; }")
        sl = QHBoxLayout(search_bar)
        sl.setContentsMargins(12, 8, 12, 8)
        sl.addWidget(QLabel("Buscar:"))
        self.person_search = QLineEdit()
        self.person_search.setPlaceholderText("Filtrar por nombre…")
        self.person_search.textChanged.connect(self.filter_persons)
        sl.addWidget(self.person_search)
        layout.addWidget(search_bar)

        layout.addWidget(QLabel("Personas identificadas (doble clic = ver fotos):"))

        self.persons_list = QListWidget()
        self.persons_list.setIconSize(QSize(56, 56))
        self.persons_list.itemDoubleClicked.connect(self.view_person_photos)
        layout.addWidget(self.persons_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_rename = QPushButton(get_icon("edit", 16), "  Renombrar")
        btn_rename.clicked.connect(self.rename_selected_person)
        btn_row.addWidget(btn_rename)

        btn_view = QPushButton(get_icon("eye", 16), "  Ver fotos")
        btn_view.clicked.connect(self.view_person_photos)
        btn_row.addWidget(btn_view)

        btn_refresh_p = QPushButton(get_icon("refresh", 16), "  Actualizar")
        btn_refresh_p.clicked.connect(self.load_persons)
        btn_row.addWidget(btn_refresh_p)

        layout.addLayout(btn_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #2d3748;")
        layout.addWidget(sep)

        hint = QLabel("Selecciona una foto en la Galería y pulsa el botón para etiquetar sus rostros.")
        hint.setStyleSheet("color: #64748b; font-size: 9pt;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        btn_label = QPushButton(get_icon("tag", 16), "  Etiquetar rostros de la foto seleccionada")
        btn_label.setStyleSheet(get_home_button_style('teal'))
        btn_label.clicked.connect(self.label_faces_for_selected_photo)
        layout.addWidget(btn_label)

        return widget

    # ── Cargar datos ──────────────────────────────────────────────────────────

    def load_statistics(self):
        stats = self.db.get_statistics()
        self.stats_photos.setText(str(stats['total_photos']))
        self.stats_faces.setText(str(stats['total_faces']))
        self.stats_persons.setText(str(stats['total_persons']))

    def load_gallery(self):
        self.photo_list.clear()
        photos = self.db.get_all_photos(limit=200)
        loaded_paths, count = set(), 0

        for photo in photos:
            if photo['file_path'] in loaded_paths:
                continue
            loaded_paths.add(photo['file_path'])
            photo_path = Path(photo['file_path'])
            if not photo_path.exists():
                continue

            scene = self.db.get_scene(photo['id'])
            scene_label = f"\n{scene['category']}" if scene else ""
            item = QListWidgetItem(photo['file_name'] + scene_label)
            item.setData(Qt.UserRole, photo['id'])

            try:
                px = QPixmap(str(photo_path))
                if not px.isNull():
                    px = px.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(px))
                    count += 1
            except Exception:
                pass

            self.photo_list.addItem(item)

        self.status_bar.showMessage(f"{count} foto(s) cargada(s)")

    def load_persons(self):
        self.persons_list.clear()
        persons = self.db.get_all_persons()

        for person in persons:
            name  = person['name'] or f"Persona {person['cluster_id']}"
            count = person['photo_count']
            item  = QListWidgetItem(f"  {name}   ({count} foto(s))")
            item.setData(Qt.UserRole, person['id'])

            try:
                conn = self.db.connect()
                row = conn.execute(
                    """SELECT f.bbox_x, f.bbox_y, f.bbox_width, f.bbox_height,
                              p.file_path
                       FROM faces f JOIN photos p ON f.photo_id = p.id
                       WHERE f.person_id = ? LIMIT 1""",
                    (person['id'],)
                ).fetchone()
                if row:
                    img_path = Path(row['file_path'])
                    if img_path.exists():
                        img = Image.open(img_path).convert("RGB")
                        x, y, w, h = row['bbox_x'], row['bbox_y'], row['bbox_width'], row['bbox_height']
                        mx, my = int(w * 0.15), int(h * 0.15)
                        crop = img.crop((
                            max(0, x - mx), max(0, y - my),
                            min(img.width, x + w + mx),
                            min(img.height, y + h + my)
                        )).resize((56, 56), Image.BILINEAR)
                        arr = np.array(crop)
                        qimg = QImage(arr.data, 56, 56, 3 * 56, QImage.Format_RGB888)
                        item.setIcon(QIcon(QPixmap.fromImage(qimg)))
            except Exception:
                pass

            self.persons_list.addItem(item)

        self.status_bar.showMessage(f"{len(persons)} persona(s) identificada(s)")

    # ── Filtros ───────────────────────────────────────────────────────────────

    def filter_gallery_by_scene(self):
        scene_category = self.scene_filter.currentData()
        self.photo_list.clear()
        if scene_category is None:
            self.load_gallery()
            return
        photos = self.db.search_photos(scene_category=scene_category)
        for photo in photos:
            photo_path = Path(photo['file_path'])
            if not photo_path.exists():
                continue
            item = QListWidgetItem(photo['file_name'])
            item.setData(Qt.UserRole, photo['id'])
            try:
                px = QPixmap(str(photo_path)).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(px))
            except Exception:
                pass
            self.photo_list.addItem(item)
        self.status_bar.showMessage(f"{len(photos)} foto(s) en {scene_category}")

    def filter_persons(self):
        text = self.person_search.text().lower()
        for i in range(self.persons_list.count()):
            item = self.persons_list.item(i)
            item.setHidden(text not in item.text().lower())

    # ── Detalle de foto ───────────────────────────────────────────────────────

    def show_photo_detail(self, item):
        self.show_selected_photo_detail()

    def show_selected_photo_detail(self):
        current = self.photo_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Selección requerida",
                                "Selecciona una foto de la galería.")
            return

        photo_id = current.data(Qt.UserRole)
        photo = self.db.get_photo_by_id(photo_id)
        if not photo:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Detalle: {photo['file_name']}")
        dlg.setGeometry(160, 80, 920, 680)
        layout = QVBoxLayout(dlg)

        photo_path = Path(photo['file_path'])
        if photo_path.exists():
            px = QPixmap(str(photo_path))
            if not px.isNull():
                px = px.scaled(860, 460, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl = QLabel()
                img_lbl.setPixmap(px)
                img_lbl.setAlignment(Qt.AlignCenter)
                scroll = QScrollArea()
                scroll.setWidget(img_lbl)
                scroll.setWidgetResizable(True)
                layout.addWidget(scroll)

        info = QGridLayout()
        row = 0

        def add_row(label, value):
            nonlocal row
            lbl = QLabel(f"<b>{label}</b>")
            lbl.setStyleSheet("color: #64748b;")
            info.addWidget(lbl, row, 0)
            info.addWidget(QLabel(str(value)), row, 1)
            row += 1

        add_row("Nombre:", photo['file_name'])
        add_row("Resolución:", f"{photo['width']} × {photo['height']} px")
        if photo['timestamp']:
            add_row("Fecha:", photo['timestamp'])

        metadata = self.db.get_metadata(photo_id)
        if metadata:
            if metadata.get('camera_make'):
                add_row("Cámara:", f"{metadata['camera_make']} {metadata.get('camera_model','')}")
            if metadata.get('gps_latitude'):
                add_row("GPS:", f"{metadata['gps_latitude']:.6f}, {metadata['gps_longitude']:.6f}")

        scene = self.db.get_scene(photo_id)
        if scene:
            add_row("Escena:", f"{scene['category']} ({scene['confidence']:.1%})")

        faces = self.db.get_faces_by_photo(photo_id)
        if faces:
            names = []
            for f in faces:
                if f['person_id']:
                    p = self.db.get_person_by_id(f['person_id'])
                    if p:
                        names.append(p['name'] or f"Persona {p['cluster_id']}")
            add_row("Personas:", ", ".join(set(names)) if names else f"{len(faces)} rostro(s)")

        layout.addLayout(info)

        btn_close = QPushButton("Cerrar")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
        dlg.exec_()

    # ── Personas ──────────────────────────────────────────────────────────────

    def rename_selected_person(self):
        current = self.persons_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Selección requerida",
                                "Selecciona una persona de la lista.")
            return
        person_id = current.data(Qt.UserRole)
        person = self.db.get_person_by_id(person_id)
        if not person:
            return
        current_name = person['name'] or f"Persona {person['cluster_id']}"
        new_name, ok = QInputDialog.getText(self, "Renombrar",
                                            f"Nuevo nombre para '{current_name}':",
                                            text=current_name)
        if ok and new_name.strip():
            self.db.update_person_name(person_id, new_name.strip())
            self.load_persons()
            self.load_statistics()

    def view_person_photos(self, _item=None):
        current = self.persons_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Selección requerida",
                                "Selecciona una persona de la lista.")
            return
        person_id = current.data(Qt.UserRole)
        person = self.db.get_person_by_id(person_id)
        if not person:
            return
        photos = self.db.search_photos(person_id=person_id)
        if not photos:
            QMessageBox.information(self, "Sin fotos",
                                    f"No hay fotos de '{person.get('name','esta persona')}'.")
            return

        name = person['name'] or f"Persona {person['cluster_id']}"
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Fotos de {name}")
        dlg.setMinimumSize(720, 520)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(f"<b>{name}</b>  —  {len(photos)} foto(s)"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(8)
        cols = 4

        for i, photo in enumerate(photos):
            cell = QWidget()
            cv = QVBoxLayout(cell)
            cv.setSpacing(3)
            cv.setContentsMargins(0, 0, 0, 0)

            img_lbl = QLabel()
            img_lbl.setFixedSize(150, 150)
            img_lbl.setAlignment(Qt.AlignCenter)
            img_lbl.setStyleSheet("border: 1px solid #2d3748; border-radius: 6px;")

            pp = Path(photo['file_path'])
            if pp.exists():
                try:
                    px = QPixmap(str(pp)).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    img_lbl.setPixmap(px)
                except Exception:
                    img_lbl.setText("Error")

            cv.addWidget(img_lbl)
            name_lbl = QLabel(photo['file_name'])
            name_lbl.setWordWrap(True)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setStyleSheet("font-size: 8pt; color: #64748b;")
            cv.addWidget(name_lbl)

            others = []
            for f in self.db.get_faces_by_photo(photo['id']):
                if f.get('person_id') and f['person_id'] != person_id:
                    p2 = self.db.get_person_by_id(f['person_id'])
                    if p2 and p2.get('name'):
                        others.append(p2['name'])
            if others:
                also = QLabel("Con: " + ", ".join(set(others)))
                also.setWordWrap(True)
                also.setAlignment(Qt.AlignCenter)
                also.setStyleSheet("font-size: 7pt; color: #3b82f6;")
                cv.addWidget(also)

            grid.addWidget(cell, i // cols, i % cols)

        scroll.setWidget(grid_w)
        layout.addWidget(scroll)
        btn_close = QPushButton("Cerrar")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
        dlg.exec_()

    def label_faces_for_selected_photo(self):
        current = self.photo_list.currentItem() if hasattr(self, 'photo_list') else None
        if not current:
            QMessageBox.information(self, "Selecciona una foto",
                                    "Ve a la pestaña Galería, selecciona una foto\n"
                                    "y luego pulsa este botón.")
            return
        photo_id = current.data(Qt.UserRole)
        faces = self.db.get_faces_by_photo(photo_id)
        if not faces:
            QMessageBox.information(self, "Sin rostros",
                                    "No se detectaron rostros en esta fotografía.")
            return
        dlg = FaceLabelingDialog(photo_id, self.db, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_persons()
            self.load_statistics()
            self.status_bar.showMessage("Etiquetas guardadas")

    # ── Importación ───────────────────────────────────────────────────────────

    def import_photos(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta con fotografías", "",
            QFileDialog.ShowDirsOnly)
        if not folder:
            return

        reply = QMessageBox.question(
            self, "Detectar rostros",
            "¿Deseas detectar rostros automáticamente?\n\n"
            "Esto puede tardar varios minutos.",
            QMessageBox.Yes | QMessageBox.No)
        process_faces = (reply == QMessageBox.Yes)

        confirm = QMessageBox.question(
            self, "Confirmar importación",
            f"Carpeta: {folder}\n"
            f"Detección de rostros: {'Sí' if process_faces else 'No'}\n\n¿Continuar?",
            QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self._start_import(Path(folder), process_faces)

    def _start_import(self, folder_path, process_faces):
        from src.ui.import_worker import ImportWorker
        self.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Importando...")
        self.import_worker = ImportWorker(folder_path, process_faces)
        self.import_worker.progress.connect(self.progress_bar.setValue)
        self.import_worker.status.connect(self.status_bar.showMessage)
        self.import_worker.finished.connect(self._on_import_finished)
        self.import_worker.error.connect(self._on_import_error)
        self.import_worker.start()

    def _on_import_finished(self, results):
        self.progress_bar.setVisible(False)
        self.setEnabled(True)
        skipped = results.get('skipped', 0)
        msg = (
            f"Importación completada:\n\n"
            f"✓ Fotos nuevas: {results['imported']}/{results['total_files']}\n"
        )
        if skipped:
            msg += f"↩ Duplicadas omitidas: {skipped}\n"
        msg += (
            f"✓ Rostros detectados: {results['total_faces']}\n"
            f"✓ Personas identificadas: {results['n_persons']}\n"
            f"✓ Escenas clasificadas: {results.get('scenes_classified', 0)}"
        )
        QMessageBox.information(self, "Importación Completada", msg)
        self.load_gallery()
        self.load_persons()
        self.load_statistics()

    def _on_import_error(self, msg):
        self.progress_bar.setVisible(False)
        self.setEnabled(True)
        QMessageBox.critical(self, "Error de Importación", f"Error:\n\n{msg}")

    # alias compatibilidad
    def start_import(self, folder_path, process_faces):
        self._start_import(folder_path, process_faces)
    def on_import_progress(self, v): self.progress_bar.setValue(v)
    def on_import_status(self, m):   self.status_bar.showMessage(m)
    def on_import_finished(self, r): self._on_import_finished(r)
    def on_import_error(self, m):    self._on_import_error(m)

    # ── Exportación ───────────────────────────────────────────────────────────

    def export_by_scene(self):
        all_photos = self.db.get_all_photos()
        if not all_photos:
            QMessageBox.warning(self, "Sin fotos", "No hay fotos importadas.")
            return

        classified   = sum(1 for p in all_photos if self.db.get_scene(p['id']) is not None)
        unclassified = len(all_photos) - classified

        reply = QMessageBox.question(
            self, "Exportar por escena",
            f"Se exportarán {len(all_photos)} fotos:\n\n"
            f"  • Con categoría: {classified}\n"
            f"  • Sin categoría: {unclassified}\n\n"
            "Selecciona la carpeta destino.",
            QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
        if reply != QMessageBox.Ok:
            return

        dest_str = QFileDialog.getExistingDirectory(
            self, "Carpeta destino", str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if not dest_str:
            return

        self._start_export(Path(dest_str))

    def _start_export(self, dest_path):
        from src.exporters.export_worker import ExportWorker
        self.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Exportando...")
        self.export_worker = ExportWorker(dest_path)
        self.export_worker.progress.connect(lambda p, m: (
            self.progress_bar.setValue(p),
            self.status_bar.showMessage(m)
        ))
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.error.connect(self._on_export_error)
        self.export_worker.start()

    def _on_export_finished(self, counts):
        self.progress_bar.setVisible(False)
        self.setEnabled(True)
        total = sum(counts.values())
        lines = "\n".join(f"  • {k}: {v}" for k, v in sorted(counts.items()) if v > 0)
        QMessageBox.information(
            self, "Exportación completada",
            f"✓ {total} fotos exportadas.\n\n{lines}\n\n"
            f"Carpeta: {self.export_worker.dest_dir / 'por_escena'}")
        self.status_bar.showMessage(f"Exportación completada: {total} fotos")

    def _on_export_error(self, msg):
        self.progress_bar.setVisible(False)
        self.setEnabled(True)
        QMessageBox.critical(self, "Error de exportación", f"Error:\n\n{msg}")

    # ── Eliminación ───────────────────────────────────────────────────────────

    def delete_all_photos(self):
        stats = self.db.get_statistics()
        total = stats.get('total_photos', 0)
        if total == 0:
            QMessageBox.information(self, "Colección vacía", "No hay fotos registradas.")
            return
        reply = QMessageBox.warning(
            self, "Eliminar todas las fotos",
            f"Se eliminarán {total} fotos y todos sus datos.\n\n"
            "Las personas con nombre se conservan.\n\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            conn = self.db.connect()
            for table in ('tags', 'scenes', 'faces', 'metadata', 'photos'):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("DELETE FROM persons WHERE name IS NULL OR TRIM(name) = ''")
            try:
                conn.execute("DELETE FROM sqlite_sequence WHERE name IN "
                             "('photos','faces','scenes','metadata','tags')")
            except Exception:
                pass
            conn.commit()
            self.load_gallery()
            self.load_persons()
            self.load_statistics()
            QMessageBox.information(self, "Completado", "Todas las fotos eliminadas.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error:\n{e}")

    def delete_selected_photos(self):
        all_photos = self.db.get_all_photos()
        if not all_photos:
            QMessageBox.information(self, "Colección vacía", "No hay fotos registradas.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Eliminar fotos específicas")
        dlg.setMinimumSize(560, 480)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Selecciona las fotos a eliminar (Ctrl+clic para múltiple):"))
        lw = QListWidget()
        lw.setSelectionMode(QListWidget.ExtendedSelection)
        lw.setIconSize(QSize(40, 40))
        for photo in all_photos:
            item = QListWidgetItem(photo['file_name'])
            item.setData(Qt.UserRole, photo['id'])
            pp = Path(photo['file_path'])
            if pp.exists():
                try:
                    px = QPixmap(str(pp)).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(px))
                except Exception:
                    pass
            lw.addItem(item)
        layout.addWidget(lw)
        sel_row = QHBoxLayout()
        b_all = QPushButton("Todo"); b_all.clicked.connect(lw.selectAll); sel_row.addWidget(b_all)
        b_none = QPushButton("Ninguno"); b_none.clicked.connect(lw.clearSelection); sel_row.addWidget(b_none)
        layout.addLayout(sel_row)
        btn_del = QPushButton("Eliminar seleccionadas")
        btn_del.setStyleSheet("QPushButton{background:#dc2626;color:white;padding:8px;border-radius:6px;font-weight:bold;}"
                              "QPushButton:hover{background:#b91c1c;}")
        btn_cancel = QPushButton("Cancelar"); btn_cancel.clicked.connect(dlg.reject)
        ar = QHBoxLayout(); ar.addWidget(btn_del); ar.addWidget(btn_cancel)
        layout.addLayout(ar)

        def do_delete():
            selected = lw.selectedItems()
            if not selected:
                QMessageBox.information(dlg, "Sin selección", "No seleccionaste ninguna foto.")
                return
            if QMessageBox.question(dlg, "Confirmar",
                f"Eliminar {len(selected)} foto(s) y todos sus datos. ¿Continuar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            deleted = 0
            for item in selected:
                try:
                    self.db.delete_photo(item.data(Qt.UserRole)); deleted += 1
                except Exception as ex:
                    logger.warning(f"Error: {ex}")
            conn = self.db.connect()
            conn.execute("DELETE FROM persons WHERE (name IS NULL OR TRIM(name)='') AND id NOT IN "
                         "(SELECT DISTINCT person_id FROM faces WHERE person_id IS NOT NULL)")
            conn.commit()
            self.load_gallery(); self.load_persons(); self.load_statistics()
            QMessageBox.information(dlg, "Completado", f"Se eliminaron {deleted} foto(s).")
            dlg.accept()

        btn_del.clicked.connect(do_delete)
        dlg.exec_()

    def delete_person_label(self):
        persons = [p for p in self.db.get_all_persons() if p.get('name')]
        if not persons:
            QMessageBox.information(self, "Sin etiquetas", "No hay personas con nombre asignado.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Gestionar etiquetas de personas")
        dlg.setMinimumSize(460, 400)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Selecciona personas (Ctrl+clic para múltiple):"))
        lw = QListWidget()
        lw.setSelectionMode(QListWidget.ExtendedSelection)
        for p in persons:
            lw.addItem(QListWidgetItem(f"{p['name']}  —  {p['photo_count']} foto(s)")).setData(Qt.UserRole, p['id']) if False else None
            item = QListWidgetItem(f"{p['name']}  —  {p['photo_count']} foto(s)")
            item.setData(Qt.UserRole, p['id'])
            lw.addItem(item)
        layout.addWidget(lw)
        chk = QCheckBox("Eliminar registro completo (los rostros quedarán sin asignar)")
        layout.addWidget(chk)
        btn_apply = QPushButton("Aplicar")
        btn_apply.setStyleSheet("QPushButton{background:#dc2626;color:white;padding:8px;border-radius:6px;font-weight:bold;}"
                                "QPushButton:hover{background:#b91c1c;}")
        btn_cancel = QPushButton("Cancelar"); btn_cancel.clicked.connect(dlg.reject)
        ar = QHBoxLayout(); ar.addWidget(btn_apply); ar.addWidget(btn_cancel)
        layout.addLayout(ar)

        def do_apply():
            selected = lw.selectedItems()
            if not selected:
                QMessageBox.information(dlg, "Sin selección", "No seleccionaste nada."); return
            full = chk.isChecked()
            if QMessageBox.question(dlg, "Confirmar",
                f"{'Eliminar' if full else 'Borrar nombre de'} {len(selected)} persona(s). ¿Continuar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            conn = self.db.connect()
            for item in selected:
                pid = item.data(Qt.UserRole)
                if full:
                    conn.execute("UPDATE faces SET person_id=NULL WHERE person_id=?", (pid,))
                    conn.execute("DELETE FROM persons WHERE id=?", (pid,))
                else:
                    conn.execute("UPDATE persons SET name=NULL WHERE id=?", (pid,))
            conn.commit()
            self.load_persons(); self.load_statistics()
            QMessageBox.information(dlg, "Completado", f"Se procesaron {len(selected)} persona(s).")
            dlg.accept()

        btn_apply.clicked.connect(do_apply)
        dlg.exec_()

    # ── Clustering ────────────────────────────────────────────────────────────

    def cluster_faces(self):
        """Reagrupa rostros respetando etiquetas manuales existentes."""
        from src.clustering.face_clustering import FaceClustering
        try:
            clusterer = FaceClustering()
            clusterer.cluster_from_database(self.db)
            stats = clusterer.get_cluster_statistics()
            self.load_statistics()
            self.load_persons()
            QMessageBox.information(
                self, "Agrupación completada",
                f"Rostros procesados: {stats.get('n_total', 0)}\n"
                f"Grupos nuevos: {stats.get('n_clusters', 0)}\n"
                f"Sin clasificar: {stats.get('n_noise', 0)}"
            )
        except Exception as e:
            logger.error(f"Error clustering: {e}")
            QMessageBox.critical(self, "Error",
                                 f"No se pudo completar la agrupación:\n{e}")

    # ── Limpieza ──────────────────────────────────────────────────────────────

    def clean_duplicates(self):
        reply = QMessageBox.question(
            self, "Limpiar duplicados",
            "Eliminar fotos duplicadas y registros huérfanos. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            import io, contextlib
            from src.clean_database import clean_database
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                clean_database()
            self.load_statistics(); self.load_gallery(); self.load_persons()
            QMessageBox.information(self, "Completado", "Base de datos limpiada.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error:\n{e}")

    # ── Ayuda ─────────────────────────────────────────────────────────────────

    def show_about(self):
        QMessageBox.about(
            self, "Acerca de PTitu",
            "<h2>PTitu — Organizador de Fotografías</h2>"
            "<p>Versión 1.0 | Universidad Autónoma de Ciudad Juárez</p>"
            "<p>Sistema de organización automática de colecciones fotográficas "
            "mediante reconocimiento facial y análisis de escenas.</p>"
            "<p><b>Tecnologías:</b> Python 3.10 · PyQt5 · MTCNN · FaceNet · "
            "VGG-16 · DBSCAN · SQLite</p>"
        )

    def closeEvent(self, event):
        self.db.close()
        event.accept()