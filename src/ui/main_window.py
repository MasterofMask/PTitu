"""
Ventana principal de la aplicación
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
    QDialog, QComboBox, QLineEdit, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QImage, QPixmap

from PIL import Image
import numpy as np

from src.core.database import DatabaseManager
from src.ui.styles import MAIN_STYLE

logger = logging.getLogger(__name__)


class FaceLabelingDialog(QDialog):
    """
    Diálogo para etiquetar cada rostro detectado en una fotografía.
    Soporta múltiples rostros por imagen.
    """

    def __init__(self, photo_id: int, db, parent=None):
        super().__init__(parent)
        self.photo_id = photo_id
        self.db = db
        self.face_widgets = []   # lista de (face_id, QComboBox)

        photo = db.get_photo_by_id(photo_id)
        self.photo_path = Path(photo['file_path']) if photo else None

        self.setWindowTitle(
            f"Etiquetar rostros — {photo['file_name'] if photo else ''}"
        )
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Asigna un nombre a cada rostro detectado:")
        title.setStyleSheet("font-weight: bold; font-size: 11pt; margin-bottom: 6px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(300)

        container = QWidget()
        self.faces_layout = QVBoxLayout(container)
        self.faces_layout.setSpacing(12)

        faces = self.db.get_faces_by_photo(self.photo_id)
        all_persons = self.db.get_all_persons()

        if not faces:
            self.faces_layout.addWidget(
                QLabel("No se detectaron rostros en esta fotografía.")
            )
        else:
            for idx, face in enumerate(faces):
                self.faces_layout.addWidget(
                    self._build_face_row(idx, face, all_persons)
                )

        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 Guardar etiquetas")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _build_face_row(self, idx: int, face: dict, all_persons: list):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background: #f8f8f8; border-radius: 6px; padding: 4px; }"
        )
        row = QHBoxLayout(frame)
        row.setSpacing(12)

        # Miniatura del rostro
        thumb_label = QLabel()
        thumb_label.setFixedSize(80, 80)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setStyleSheet("border: 1px solid #ccc; background: #eee;")

        if self.photo_path and self.photo_path.exists():
            try:
                img = Image.open(self.photo_path).convert("RGB")
                x  = face['bbox_x']
                y  = face['bbox_y']
                w  = face['bbox_width']
                h  = face['bbox_height']
                mx = int(w * 0.15)
                my = int(h * 0.15)
                x1 = max(0, x - mx);  y1 = max(0, y - my)
                x2 = min(img.width, x + w + mx)
                y2 = min(img.height, y + h + my)
                crop = img.crop((x1, y1, x2, y2)).resize((80, 80), Image.BILINEAR)
                arr  = np.array(crop)
                h_c, w_c, ch = arr.shape
                qimg = QImage(arr.data, w_c, h_c, ch * w_c, QImage.Format_RGB888)
                thumb_label.setPixmap(QPixmap.fromImage(qimg))
            except Exception:
                thumb_label.setText("?")

        row.addWidget(thumb_label)

        # Columna de info + nombre
        info_col = QVBoxLayout()

        conf_label = QLabel(f"Rostro #{idx + 1}  —  confianza: {face['confidence']:.0%}")
        conf_label.setStyleSheet("color: #555; font-size: 9pt;")
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
            display = p['name'] or f"Persona {p['cluster_id']}"
            combo.addItem(display, userData=p['id'])

        if current_name:
            idx_combo = combo.findText(current_name)
            if idx_combo >= 0:
                combo.setCurrentIndex(idx_combo)
            else:
                combo.setCurrentText(current_name)

        combo.setPlaceholderText("Escribe o selecciona un nombre…")
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

            existing = self._find_person_by_name(name)
            if existing:
                person_id = existing['id']
            else:
                max_cluster = self._next_cluster_id()
                person_id = self.db.insert_person(
                    cluster_id=max_cluster, name=name
                )

            self.db.update_face_person(face_id, person_id)
            saved += 1

        if saved:
            QMessageBox.information(
                self, "Guardado",
                f"✓ {saved} etiqueta(s) guardada(s)."
            )
            self.accept()
        else:
            self.reject()

    def _find_person_by_name(self, name: str):
        for p in self.db.get_all_persons():
            if p.get('name') == name:
                return p
        return None

    def _next_cluster_id(self) -> int:
        """
        Genera un cluster_id único para personas creadas manualmente.
        Maneja cluster_id corruptos (bytes) sin lanzar excepción.
        """
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

class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("PTITU - Organizador de Fotografías")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(MAIN_STYLE)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Barra de menú
        self.create_menu_bar()
        
        # Título y estadísticas
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📸 Organizador de Fotografías")
        title_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #0078d4;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Panel de estadísticas
        self.stats_widget = self.create_stats_widget()
        header_layout.addWidget(self.stats_widget)
        
        main_layout.addLayout(header_layout)
        
        # Pestañas principales
        self.tabs = QTabWidget()
        
        # Pestaña: Inicio
        self.home_tab = self.create_home_tab()
        self.tabs.addTab(self.home_tab, "🏠 Inicio")
        
        # Pestaña: Galería
        self.gallery_tab = self.create_gallery_tab()
        self.tabs.addTab(self.gallery_tab, "🖼️ Galería")
        
        # Pestaña: Personas
        self.persons_tab = self.create_persons_tab()
        self.tabs.addTab(self.persons_tab, "👥 Personas")
        
        main_layout.addWidget(self.tabs)
        
        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
        
        # Progress bar (oculta por defecto)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
    
    def create_menu_bar(self):
        """Crea la barra de menú"""
        menubar = self.menuBar()
        
        # Menú Archivo
        file_menu = menubar.addMenu("&Archivo")
        
        import_action = QAction("&Importar Fotos", self)
        import_action.triggered.connect(self.import_photos)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menú Herramientas
        # Menú Herramientas
        tools_menu = menubar.addMenu("&Herramientas")

        cluster_action = QAction("⚙️ &Agrupar Personas", self)
        cluster_action.triggered.connect(self.cluster_faces)
        tools_menu.addAction(cluster_action)

        tools_menu.addSeparator()

        clean_action = QAction("🧹 &Limpiar Duplicados", self)
        clean_action.triggered.connect(self.clean_duplicates)
        tools_menu.addAction(clean_action)

        tools_menu.addSeparator()

        del_selected_action = QAction("🗑️ Eliminar fotos seleccionadas...", self)
        del_selected_action.triggered.connect(self.delete_selected_photos)
        tools_menu.addAction(del_selected_action)

        del_all_action = QAction("⚠️ Eliminar TODAS las fotos", self)
        del_all_action.triggered.connect(self.delete_all_photos)
        tools_menu.addAction(del_all_action)

        tools_menu.addSeparator()

        del_person_action = QAction("👤 Gestionar etiquetas de personas...", self)
        del_person_action.triggered.connect(self.delete_person_label)
        tools_menu.addAction(del_person_action)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("&Ayuda")
        
        about_action = QAction("&Acerca de", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def clean_duplicates(self):
        """Limpia duplicados de la base de datos"""
        reply = QMessageBox.question(
            self,
            "Limpiar Duplicados",
            "Esto eliminará fotos duplicadas y registros huérfanos.\n\n"
            "¿Continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                from src.clean_database import clean_database
                
                # Ejecutar limpieza (capturar output)
                import io
                import contextlib
                
                f = io.StringIO()
                with contextlib.redirect_stdout(f):
                    clean_database()
                
                output = f.getvalue()
                
                # Mostrar resultado
                QMessageBox.information(
                    self,
                    "Limpieza Completada",
                    "La base de datos ha sido limpiada.\n\n"
                    "Revisa la consola para ver detalles."
                )
                
                # Actualizar vistas
                self.load_statistics()
                self.load_gallery()
                self.load_persons()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error durante la limpieza:\n{str(e)}"
            )
    
    def create_stats_widget(self):
        """Crea el widget de estadísticas"""
        stats_group = QGroupBox("Estadísticas")
        stats_layout = QGridLayout()
        
        self.stats_photos = QLabel("0")
        self.stats_faces = QLabel("0")
        self.stats_persons = QLabel("0")
        
        stats_layout.addWidget(QLabel("📷 Fotos:"), 0, 0)
        stats_layout.addWidget(self.stats_photos, 0, 1)
        
        stats_layout.addWidget(QLabel("👤 Rostros:"), 1, 0)
        stats_layout.addWidget(self.stats_faces, 1, 1)
        
        stats_layout.addWidget(QLabel("👥 Personas:"), 2, 0)
        stats_layout.addWidget(self.stats_persons, 2, 1)
        
        stats_group.setLayout(stats_layout)
        return stats_group
    
    def create_home_tab(self):
        """Crea la pestaña de inicio"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Botones principales
        btn_layout = QGridLayout()
        
        # Botón: Importar Fotos
        btn_import = QPushButton("📁 Importar Fotos")
        btn_import.setMinimumHeight(80)
        btn_import.setStyleSheet("font-size: 14pt;")
        btn_import.clicked.connect(self.import_photos)
        btn_layout.addWidget(btn_import, 0, 0)
        
        # Botón: Ver Galería
        btn_gallery = QPushButton("🖼️ Ver Galería")
        btn_gallery.setMinimumHeight(80)
        btn_gallery.setStyleSheet("font-size: 14pt;")
        btn_gallery.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        btn_layout.addWidget(btn_gallery, 0, 1)
        
        # Botón: Ver Personas
        btn_persons = QPushButton("👥 Ver Personas")
        btn_persons.setMinimumHeight(80)
        btn_persons.setStyleSheet("font-size: 14pt;")
        btn_persons.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        btn_layout.addWidget(btn_persons, 1, 0)
        
        # Botón: Agrupar
        btn_cluster = QPushButton("⚙️ Agrupar Personas")
        btn_cluster.setMinimumHeight(80)
        btn_cluster.setStyleSheet("font-size: 14pt;")
        btn_cluster.clicked.connect(self.cluster_faces)
        btn_layout.addWidget(btn_cluster, 1, 1)

        #Botón: Exportar
        btn_export = QPushButton("📂 Exportar por Escena")
        btn_export.setMinimumHeight(80)
        btn_export.setStyleSheet("font-size: 14pt;")
        btn_export.clicked.connect(self.export_by_scene)
        btn_layout.addWidget(btn_export, 2, 0, 1, 2)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_gallery_tab(self):
        """Crea la pestaña de galería"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Filtros de búsqueda
        filter_layout = QHBoxLayout()
        
        # Filtro por escena
        filter_layout.addWidget(QLabel("Filtrar por escena:"))
        self.scene_filter = QComboBox() 
        self.scene_filter.addItem("Todas", None)
        self.scene_filter.addItem("Interiores", "interiores")
        self.scene_filter.addItem("Exteriores", "exteriores")
        self.scene_filter.addItem("Restaurantes", "restaurantes")
        self.scene_filter.addItem("Eventos Sociales", "eventos_sociales")
        self.scene_filter.addItem("Actividades Deportivas", "actividades_deportivas")
        self.scene_filter.currentIndexChanged.connect(self.filter_gallery_by_scene)
        filter_layout.addWidget(self.scene_filter)
        
        filter_layout.addStretch()
        
        layout.addLayout(filter_layout)
        
        # Lista de fotos
        self.photo_list = QListWidget()
        self.photo_list.setViewMode(QListWidget.IconMode)
        self.photo_list.setIconSize(QSize(200, 200))
        self.photo_list.setResizeMode(QListWidget.Adjust)
        self.photo_list.setSpacing(10)
        self.photo_list.itemDoubleClicked.connect(self.show_photo_detail)
        
        layout.addWidget(QLabel("Todas las fotografías:"))
        layout.addWidget(self.photo_list)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_gallery)
        btn_layout.addWidget(btn_refresh)
        
        btn_view = QPushButton("👁️ Ver Detalle")
        btn_view.clicked.connect(self.show_selected_photo_detail)
        btn_layout.addWidget(btn_view)
        
        layout.addLayout(btn_layout)
        
        widget.setLayout(layout)
        return widget
    
    def create_persons_tab(self):
        """Pestaña de personas con galería y etiquetado multi-rostro."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Buscador
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("🔍 Buscar:"))
        self.person_search = QLineEdit()
        self.person_search.setPlaceholderText("Filtrar por nombre…")
        self.person_search.textChanged.connect(self.filter_persons)
        search_row.addWidget(self.person_search)
        layout.addLayout(search_row)

        # Lista de personas
        layout.addWidget(QLabel("Personas identificadas (doble clic = ver fotos):"))
        self.persons_list = QListWidget()
        self.persons_list.setIconSize(QSize(64, 64))
        self.persons_list.itemDoubleClicked.connect(self.view_person_photos)
        layout.addWidget(self.persons_list)

        # Botones superiores
        btn_row = QHBoxLayout()
        btn_rename = QPushButton("✏️ Renombrar")
        btn_rename.clicked.connect(self.rename_selected_person)
        btn_row.addWidget(btn_rename)
        btn_view = QPushButton("🖼️ Ver fotos")
        btn_view.clicked.connect(self.view_person_photos)
        btn_row.addWidget(btn_view)
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_persons)
        btn_row.addWidget(btn_refresh)
        layout.addLayout(btn_row)

        # Sección de etiquetado manual
        sep = QLabel("── Etiquetado manual de rostros ──")
        sep.setAlignment(Qt.AlignCenter)
        sep.setStyleSheet("color: #888; margin-top: 8px;")
        layout.addWidget(sep)

        hint = QLabel(
            "Selecciona una foto en la pestaña Galería y pulsa el botón de abajo\n"
            "para asignar nombres a cada rostro detectado en ella."
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #555; font-size: 9pt;")
        layout.addWidget(hint)

        btn_label = QPushButton("🏷️  Etiquetar rostros de la foto seleccionada")
        btn_label.setStyleSheet(
            "QPushButton { background: #0078d4; color: white; "
            "padding: 8px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #005fa3; }"
        )
        btn_label.clicked.connect(self.label_faces_for_selected_photo)
        layout.addWidget(btn_label)

        widget.setLayout(layout)
        return widget
    
    # ==================== MÉTODOS DE CARGA ====================
    
    def load_statistics(self):
        """Carga las estadísticas desde la base de datos"""
        stats = self.db.get_statistics()
        
        self.stats_photos.setText(str(stats['total_photos']))
        self.stats_faces.setText(str(stats['total_faces']))
        self.stats_persons.setText(str(stats['total_persons']))
    
    def load_gallery(self):
        """Carga la galería de fotos"""
        self.photo_list.clear()
        
        # Obtener fotos únicas de la base de datos
        photos = self.db.get_all_photos(limit=100)
        
        # Usar un set para evitar duplicados
        loaded_paths = set()
        loaded_count = 0
        
        for photo in photos:
            # Evitar duplicados
            if photo['file_path'] in loaded_paths:
                continue
            
            loaded_paths.add(photo['file_path'])
            
            # Verificar que el archivo existe
            photo_path = Path(photo['file_path'])
            if not photo_path.exists():
                continue
            
            # Crear item con información
            display_name = photo['file_name']
            
            # Añadir información de escena si existe
            scene = self.db.get_scene(photo['id'])
            if scene:
                display_name += f"\n📍 {scene['category']}"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, photo['id'])  # Guardar ID para referencia
            
            # Intentar cargar thumbnail
            try:
                pixmap = QPixmap(str(photo_path))
                if not pixmap.isNull():
                    # Escalar manteniendo aspecto
                    pixmap = pixmap.scaled(
                        200, 200, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    item.setIcon(QIcon(pixmap))
                    loaded_count += 1
            except Exception as e:
                logger.warning(f"Error cargando thumbnail de {photo['file_name']}: {e}")
            
            self.photo_list.addItem(item)
        
        self.status_bar.showMessage(f"Cargadas {loaded_count} fotos únicas")
    
    def load_persons(self):
        """Recarga la lista de personas con thumbnail del primer rostro."""
        self.persons_list.clear()
        persons = self.db.get_all_persons()

        for person in persons:
            name  = person['name'] or f"Persona {person['cluster_id']}"
            count = person['photo_count']
            item  = QListWidgetItem(f"{name}  ({count} foto(s))")
            item.setData(Qt.UserRole, person['id'])

            # Thumbnail: recortar primer rostro de esta persona
            try:
                conn = self.db.connect()
                row = conn.execute(
                    """SELECT f.bbox_x, f.bbox_y, f.bbox_width, f.bbox_height,
                              p.file_path
                       FROM faces f
                       JOIN photos p ON f.photo_id = p.id
                       WHERE f.person_id = ? LIMIT 1""",
                    (person['id'],)
                ).fetchone()
                if row:
                    img_path = Path(row['file_path'])
                    if img_path.exists():
                        img = Image.open(img_path).convert("RGB")
                        x, y, w, h = (row['bbox_x'], row['bbox_y'],
                                      row['bbox_width'], row['bbox_height'])
                        mx = int(w * 0.15); my = int(h * 0.15)
                        crop = img.crop((
                            max(0, x - mx), max(0, y - my),
                            min(img.width,  x + w + mx),
                            min(img.height, y + h + my)
                        )).resize((64, 64), Image.BILINEAR)
                        arr  = np.array(crop)
                        qimg = QImage(arr.data, 64, 64, 3 * 64, QImage.Format_RGB888)
                        item.setIcon(QIcon(QPixmap.fromImage(qimg)))
            except Exception:
                pass

            self.persons_list.addItem(item)

        self.status_bar.showMessage(f"{len(persons)} persona(s) identificada(s)")
    
    # ==================== MÉTODOS DE FILTRADO ====================
    
    def filter_gallery_by_scene(self):
        """Filtra la galería por tipo de escena"""
        scene_category = self.scene_filter.currentData()
        
        self.photo_list.clear()
        
        if scene_category is None:
            # Mostrar todas
            self.load_gallery()
        else:
            # Filtrar por escena
            photos = self.db.search_photos(scene_category=scene_category)
            
            for photo in photos:
                photo_path = Path(photo['file_path'])
                if not photo_path.exists():
                    continue
                
                item = QListWidgetItem(photo['file_name'])
                item.setData(Qt.UserRole, photo['id'])
                
                try:
                    pixmap = QPixmap(str(photo_path))
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(pixmap))
                except:
                    pass
                
                self.photo_list.addItem(item)
            
            self.status_bar.showMessage(f"{len(photos)} foto(s) en {scene_category}")
    
    def filter_persons(self):
        """Filtra la lista de personas por búsqueda"""
        search_text = self.person_search.text().lower()
        
        for i in range(self.persons_list.count()):
            item = self.persons_list.item(i)
            item_text = item.text().lower()
            
            # Mostrar/ocultar según coincidencia
            item.setHidden(search_text not in item_text)
    
    # ==================== MÉTODOS DE VISUALIZACIÓN ====================
    
    def show_photo_detail(self, item):
        """Muestra detalle de foto al hacer doble clic"""
        self.show_selected_photo_detail()
    
    def show_selected_photo_detail(self):
        """Muestra ventana con detalle de la foto seleccionada"""
        current_item = self.photo_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Por favor, selecciona una foto de la galería."
            )
            return
        
        photo_id = current_item.data(Qt.UserRole)
        photo = self.db.get_photo_by_id(photo_id)
        
        if not photo:
            QMessageBox.warning(self, "Error", "No se pudo cargar la información de la foto.")
            return
        
        # Crear diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalle: {photo['file_name']}")
        dialog.setGeometry(200, 100, 900, 700)
        
        layout = QVBoxLayout()
        
        # Imagen
        photo_path = Path(photo['file_path'])
        if photo_path.exists():
            pixmap = QPixmap(str(photo_path))
            if not pixmap.isNull():
                # Escalar a tamaño razonable
                pixmap = pixmap.scaled(800, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignCenter)
                
                scroll = QScrollArea()
                scroll.setWidget(img_label)
                scroll.setWidgetResizable(True)
                
                layout.addWidget(scroll)
        
        # Información
        info_layout = QGridLayout()
        row = 0
        
        info_layout.addWidget(QLabel("<b>Nombre:</b>"), row, 0)
        info_layout.addWidget(QLabel(photo['file_name']), row, 1)
        row += 1
        
        if photo['timestamp']:
            info_layout.addWidget(QLabel("<b>Fecha:</b>"), row, 0)
            info_layout.addWidget(QLabel(str(photo['timestamp'])), row, 1)
            row += 1
        
        info_layout.addWidget(QLabel("<b>Resolución:</b>"), row, 0)
        info_layout.addWidget(QLabel(f"{photo['width']} x {photo['height']} px"), row, 1)
        row += 1
        
        # Metadatos
        metadata = self.db.get_metadata(photo_id)
        if metadata:
            if metadata['camera_make']:
                info_layout.addWidget(QLabel("<b>Cámara:</b>"), row, 0)
                info_layout.addWidget(
                    QLabel(f"{metadata['camera_make']} {metadata.get('camera_model', '')}"), 
                    row, 1
                )
                row += 1
            
            if metadata['gps_latitude'] and metadata['gps_longitude']:
                info_layout.addWidget(QLabel("<b>Ubicación GPS:</b>"), row, 0)
                info_layout.addWidget(
                    QLabel(f"{metadata['gps_latitude']:.6f}, {metadata['gps_longitude']:.6f}"),
                    row, 1
                )
                row += 1
        
        # Escena
        scene = self.db.get_scene(photo_id)
        if scene:
            info_layout.addWidget(QLabel("<b>Escena:</b>"), row, 0)
            info_layout.addWidget(
                QLabel(f"{scene['category']} ({scene['confidence']:.1%})"),
                row, 1
            )
            row += 1
        
        # Rostros detectados
        faces = self.db.get_faces_by_photo(photo_id)
        if faces:
            info_layout.addWidget(QLabel("<b>Personas:</b>"), row, 0)
            
            persons_text = []
            for face in faces:
                if face['person_id']:
                    person = self.db.get_person_by_id(face['person_id'])
                    if person:
                        name = person['name'] or f"Persona {person['cluster_id']}"
                        persons_text.append(name)
            
            if persons_text:
                info_layout.addWidget(QLabel(", ".join(set(persons_text))), row, 1)
            else:
                info_layout.addWidget(QLabel(f"{len(faces)} rostro(s) detectado(s)"), row, 1)
            row += 1
        
        layout.addLayout(info_layout)
        
        # Botón cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def rename_person(self, item):
        """Renombra una persona al hacer doble clic"""
        self.rename_selected_person()
    
    def rename_selected_person(self):
        """Renombra la persona seleccionada."""
        current_item = self.persons_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selección requerida",
                                "Selecciona una persona de la lista.")
            return

        person_id = current_item.data(Qt.UserRole)
        person    = self.db.get_person_by_id(person_id)
        if not person:
            return

        current_name = person['name'] or f"Persona {person['cluster_id']}"
        new_name, ok = QInputDialog.getText(
            self, "Renombrar",
            f"Nuevo nombre para '{current_name}':",
            text=current_name
        )
        if ok and new_name.strip():
            self.db.update_person_name(person_id, new_name.strip())
            self.load_persons()
            self.load_statistics()
            self.status_bar.showMessage(f"Renombrado a '{new_name.strip()}'")






    
    def view_person_photos(self, _item=None):
        """Abre galería con todas las fotos de la persona seleccionada."""
        current_item = self.persons_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selección requerida",
                                "Selecciona una persona de la lista.")
            return

        person_id = current_item.data(Qt.UserRole)
        person    = self.db.get_person_by_id(person_id)
        if not person:
            return

        photos = self.db.search_photos(person_id=person_id)
        if not photos:
            QMessageBox.information(
                self, "Sin fotos",
                f"No hay fotos de '{person['name'] or 'esta persona'}'."
            )
            return

        name = person['name'] or f"Persona {person['cluster_id']}"

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Fotos de {name}")
        dlg.setMinimumSize(700, 500)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(f"<b>{name}</b> — {len(photos)} foto(s)"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(8)

        cols = 4
        for i, photo in enumerate(photos):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setSpacing(2)

            img_label = QLabel()
            img_label.setFixedSize(150, 150)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("border: 1px solid #ccc;")

            photo_path = Path(photo['file_path'])
            if photo_path.exists():
                try:
                    px = QPixmap(str(photo_path)).scaled(
                        150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    img_label.setPixmap(px)
                except Exception:
                    img_label.setText("Error")

            cell_layout.addWidget(img_label)

            name_lbl = QLabel(photo['file_name'])
            name_lbl.setWordWrap(True)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setStyleSheet("font-size: 8pt; color: #333;")
            cell_layout.addWidget(name_lbl)

            # Mostrar otras personas en esta foto
            faces_in_photo = self.db.get_faces_by_photo(photo['id'])
            others = []
            for f in faces_in_photo:
                if f.get('person_id') and f['person_id'] != person_id:
                    p2 = self.db.get_person_by_id(f['person_id'])
                    if p2:
                        others.append(p2['name'] or f"Persona {p2['cluster_id']}")
            if others:
                also_lbl = QLabel("También: " + ", ".join(set(others)))
                also_lbl.setWordWrap(True)
                also_lbl.setAlignment(Qt.AlignCenter)
                also_lbl.setStyleSheet("font-size: 7pt; color: #0078d4;")
                cell_layout.addWidget(also_lbl)

            grid.addWidget(cell, i // cols, i % cols)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dlg.close)
        layout.addWidget(btn_close)
        dlg.exec_()

    def label_faces_for_selected_photo(self):
        """
        Abre el diálogo de etiquetado para la foto seleccionada en Galería.
        """
        current_item = None
        if hasattr(self, 'photo_list'):
            current_item = self.photo_list.currentItem()

        if not current_item:
            QMessageBox.information(
                self, "Selecciona una foto",
                "Ve a la pestaña Galería, selecciona una foto\n"
                "y luego pulsa este botón."
            )
            return

        photo_id = current_item.data(Qt.UserRole)
        faces = self.db.get_faces_by_photo(photo_id)
        if not faces:
            QMessageBox.information(
                self, "Sin rostros",
                "No se detectaron rostros en esta fotografía.\n"
                "Verifica que fue importada con detección de rostros activa."
            )
            return

        dlg = FaceLabelingDialog(photo_id, self.db, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self.load_persons()
            self.load_statistics()
            self.status_bar.showMessage("Etiquetas guardadas correctamente")   
    
    # ==================== MÉTODOS DE IMPORTACIÓN ====================
    
    def import_photos(self):
        """Importa fotos desde una carpeta"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta con fotografías",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if not folder:
            return
        
        # Preguntar si detectar rostros
        reply = QMessageBox.question(
            self,
            "Procesar fotos",
            "¿Deseas detectar rostros automáticamente?\n\n"
            "Esto puede tardar varios minutos dependiendo\n"
            "del número de fotos.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        process_faces = (reply == QMessageBox.Yes)
        
        # Confirmar
        confirm = QMessageBox.question(
            self,
            "Confirmar importación",
            f"Se importarán fotos desde:\n{folder}\n\n"
            f"Detección de rostros: {'Sí' if process_faces else 'No'}\n\n"
            "¿Continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        # Iniciar importación
        self.start_import(Path(folder), process_faces)
    
    def start_import(self, folder_path, process_faces):
        """Inicia el proceso de importación"""
        from src.ui.import_worker import ImportWorker
        
        # Deshabilitar UI durante importación
        self.setEnabled(False)
        
        # Mostrar barra de progreso
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Iniciando importación...")
        
        # Crear worker
        self.import_worker = ImportWorker(folder_path, process_faces)
        
        # Conectar señales
        self.import_worker.progress.connect(self.on_import_progress)
        self.import_worker.status.connect(self.on_import_status)
        self.import_worker.finished.connect(self.on_import_finished)
        self.import_worker.error.connect(self.on_import_error)
        
        # Iniciar
        self.import_worker.start()
    
    def on_import_progress(self, value):
        """Actualiza la barra de progreso"""
        self.progress_bar.setValue(value)
    
    def on_import_status(self, message):
        """Actualiza el mensaje de estado"""
        self.status_bar.showMessage(message)
    
    def on_import_finished(self, results):
        """Maneja la finalización de la importación"""
        self.progress_bar.setVisible(False)
        self.setEnabled(True)

        skipped = results.get('skipped', 0)
        skipped_line = f"↩ Duplicadas omitidas: {skipped}\n" if skipped > 0 else ""

        message = (
            f"Importación completada:\n\n"
            f"✓ Fotos nuevas importadas: {results['imported']}/{results['total_files']}\n"
            f"{skipped_line}"
            f"✓ Rostros detectados: {results['total_faces']}\n"
            f"✓ Personas identificadas: {results['n_persons']}\n"
            f"✓ Escenas clasificadas: {results.get('scenes_classified', 0)}"
        )

        QMessageBox.information(self, "Importación Completada", message)

        # Recargar galería con datos actualizados
        self.load_gallery()
        self.load_persons()
    
    def on_import_error(self, error_message):
        """Maneja errores durante la importación"""
        self.progress_bar.setVisible(False)
        self.setEnabled(True)

        QMessageBox.critical(self,"Error de Importación",f"Ocurrió un error durante la importación:\n\n{error_message}")

        self.status_bar.showMessage("Error en importación")


# ==================== MÉTODOS DE EXPORTACIÓN ====================

    def export_by_scene(self):
        """Abre diálogo para seleccionar destino y exporta fotos por escena."""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox

        # Verificar que hay fotos procesadas
        stats = self.db.get_statistics()
        scenes = stats.get('scenes_distribution', {})
        total_classified = sum(scenes.values())

        if total_classified == 0:
            QMessageBox.warning(
                self,
                "Sin fotos clasificadas",
                "No hay fotos clasificadas para exportar."
            )
            return

        # Rest of your method code here...

    def _start_export(self, dest_path):
        """Inicia el worker de exportación."""
        from src.exporters.export_worker import ExportWorker

        self.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Iniciando exportación...")

        self.export_worker = ExportWorker(dest_path)
        self.export_worker.progress.connect(self._on_export_progress)
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.error.connect(self._on_export_error)
        self.export_worker.start()


    def _on_export_progress(self, pct: int, message: str):
        """Actualiza barra de progreso durante la exportación."""
        self.progress_bar.setValue(pct)
        self.status_bar.showMessage(message)


    def _on_export_finished(self, counts: dict):
        """Muestra resultado al terminar la exportación."""
        from PyQt5.QtWidgets import QMessageBox

        self.progress_bar.setVisible(False)
        self.setEnabled(True)

        total = sum(counts.values())
        lines = "\n".join(
            f"  • {folder}: {n} fotos"
            for folder, n in sorted(counts.items())
            if n > 0
        )

        QMessageBox.information(
            self,
            "Exportación completada",
            f"✓ {total} fotos exportadas exitosamente.\n\n"
            f"Distribución:\n{lines}\n\n"
            f"Carpeta: {self.export_worker.dest_dir / 'por_escena'}",
        )
        self.status_bar.showMessage(f"Exportación completada: {total} fotos")


    def _on_export_error(self, message: str):
        """Muestra error si falla la exportación."""
        from PyQt5.QtWidgets import QMessageBox

        self.progress_bar.setVisible(False)
        self.setEnabled(True)

        QMessageBox.critical(
            self,
            "Error de exportación",
            f"Ocurrió un error durante la exportación:\n\n{message}",
        )
        self.status_bar.showMessage("Error en exportación")


    def update_scene_filter(self):

        # Reemplaza los addItem del scene_filter con estos:
        self.scene_filter.clear()
        self.scene_filter.addItem("Todas",                    None)
        self.scene_filter.addItem("Interiores",            "interiores")
        self.scene_filter.addItem("Exteriores",            "exteriores")
        self.scene_filter.addItem("Restaurantes",          "restaurantes")
        self.scene_filter.addItem("Eventos Sociales",      "eventos_sociales")
        self.scene_filter.addItem("Actividades Deportivas", "actividades_deportivas")




# ==================== MÉTODOS DE CLUSTERING ====================
    
    def cluster_faces(self):
        """Ejecuta clustering de rostros"""
        from src.clustering.face_clustering import FaceClustering
        
        reply = QMessageBox.question(
            self,
            "Agrupar Personas",
            "¿Deseas agrupar los rostros detectados para identificar personas?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                clusterer = FaceClustering()
                clusters = clusterer.cluster_from_database(self.db)
                
                stats = clusterer.get_cluster_statistics()
                
                QMessageBox.information(
                    self,
                    "Clustering Completado",
                    f"Resultados:\n\n"
                    f"• Rostros procesados: {stats['n_total']}\n"
                    f"• Personas identificadas: {stats['n_clusters']}\n"
                    f"• Rostros sin clasificar: {stats['n_noise']}"
                )
                
                self.load_statistics()
                self.load_persons()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Error durante el clustering:\n{str(e)}"
                )

# ==================== MÉTODOS DE ELIMINACIÓN ====================
    def delete_all_photos(self):
        """Elimina todas las fotos y datos asociados de la base de datos."""
        stats = self.db.get_statistics()
        total = stats.get('total_photos', 0)

        if total == 0:
            QMessageBox.information(self, "Colección vacía",
                                    "No hay fotos registradas.")
            return

        reply = QMessageBox.warning(
            self,
            "Eliminar todas las fotos",
            f"Se eliminarán los {total} registros de fotos junto con\n"
            f"sus rostros, escenas y metadatos.\n\n"
            f"Las personas con nombre asignado se conservan.\n\n"
            f"Esta acción no se puede deshacer. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            conn = self.db.connect()
            for table in ('tags', 'scenes', 'faces', 'metadata', 'photos'):
                conn.execute(f"DELETE FROM {table}")
            conn.execute(
                "DELETE FROM persons WHERE name IS NULL OR TRIM(name) = ''"
            )
            try:
                conn.execute(
                    "DELETE FROM sqlite_sequence WHERE name IN "
                    "('photos','faces','scenes','metadata','tags')"
                )
            except Exception:
                pass
            conn.commit()
            self.load_gallery()
            self.load_persons()
            self.load_statistics()
            self.status_bar.showMessage("Colección eliminada")
            QMessageBox.information(self, "Completado",
                                    "Todas las fotos han sido eliminadas.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al eliminar:\n{e}") 

    def delete_selected_photos(self):
        """Abre un diálogo para seleccionar y eliminar fotos individualmente."""
        all_photos = self.db.get_all_photos()
        if not all_photos:
            QMessageBox.information(self, "Colección vacía",
                                    "No hay fotos registradas.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Eliminar fotos específicas")
        dlg.setMinimumSize(560, 500)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel(
            "Selecciona las fotos a eliminar (Ctrl+clic para múltiple):"
        ))

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        list_widget.setIconSize(QSize(48, 48))

        for photo in all_photos:
            item = QListWidgetItem(photo['file_name'])
            item.setData(Qt.UserRole, photo['id'])
            p = Path(photo['file_path'])
            if p.exists():
                try:
                    px = QPixmap(str(p)).scaled(
                        48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    item.setIcon(QIcon(px))
                except Exception:
                    pass
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        sel_row = QHBoxLayout()
        btn_all = QPushButton("Seleccionar todo")
        btn_all.clicked.connect(list_widget.selectAll)
        btn_none = QPushButton("Limpiar selección")
        btn_none.clicked.connect(list_widget.clearSelection)
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        layout.addLayout(sel_row)

        btn_del = QPushButton("Eliminar seleccionadas")
        btn_del.setStyleSheet(
            "QPushButton{background:#c42b1c;color:white;padding:8px;"
            "border-radius:4px;font-weight:bold;}"
            "QPushButton:hover{background:#a01010;}"
        )
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(dlg.reject)

        act_row = QHBoxLayout()
        act_row.addWidget(btn_del)
        act_row.addWidget(btn_cancel)
        layout.addLayout(act_row)

        def do_delete():
            selected = list_widget.selectedItems()
            if not selected:
                QMessageBox.information(dlg, "Sin selección",
                                        "No has seleccionado ninguna foto.")
                return

            confirm = QMessageBox.question(
                dlg, "Confirmar",
                f"Se eliminarán {len(selected)} foto(s) y todos sus datos\n"
                f"(rostros, escenas, metadatos). ¿Continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

            deleted = 0
            for item in selected:
                try:
                    self.db.delete_photo(item.data(Qt.UserRole))
                    deleted += 1
                except Exception as ex:
                    logger.warning(f"Error borrando foto: {ex}")

            # Limpiar personas sin nombre sin rostros
            conn = self.db.connect()
            conn.execute("""
                DELETE FROM persons
                WHERE (name IS NULL OR TRIM(name) = '')
                  AND id NOT IN (
                      SELECT DISTINCT person_id FROM faces
                      WHERE person_id IS NOT NULL)
            """)
            conn.commit()

            self.load_gallery()
            self.load_persons()
            self.load_statistics()
            self.status_bar.showMessage(f"{deleted} foto(s) eliminada(s)")
            QMessageBox.information(dlg, "Completado",
                                    f"Se eliminaron {deleted} foto(s).")
            dlg.accept()

        btn_del.clicked.connect(do_delete)
        dlg.exec_()

    def delete_person_label(self):
        """
        Diálogo para gestionar etiquetas de personas.
        Opciones:
          - Solo borrar el nombre (la agrupación de rostros se mantiene)
          - Eliminar persona completa (rostros quedan sin asignar)
        """
        persons = [p for p in self.db.get_all_persons() if p.get('name')]
        if not persons:
            QMessageBox.information(self, "Sin etiquetas",
                                    "No hay personas con nombre asignado.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Gestionar etiquetas de personas")
        dlg.setMinimumSize(480, 440)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel(
            "Selecciona las personas y elige la acción a realizar\n"
            "(Ctrl+clic para selección múltiple):"
        ))

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        list_widget.setIconSize(QSize(48, 48))

        for p in persons:
            item = QListWidgetItem(
                f"{p['name']}  —  {p['photo_count']} foto(s)"
            )
            item.setData(Qt.UserRole, p['id'])
            # Thumbnail del primer rostro
            try:
                conn = self.db.connect()
                row = conn.execute(
                    """SELECT f.bbox_x, f.bbox_y, f.bbox_width, f.bbox_height,
                              ph.file_path
                       FROM faces f JOIN photos ph ON f.photo_id = ph.id
                       WHERE f.person_id = ? LIMIT 1""",
                    (p['id'],)
                ).fetchone()
                if row:
                    img_path = Path(row['file_path'])
                    if img_path.exists():
                        img = Image.open(img_path).convert("RGB")
                        x, y, w, h = (row['bbox_x'], row['bbox_y'],
                                      row['bbox_width'], row['bbox_height'])
                        mx, my = int(w * .15), int(h * .15)
                        crop = img.crop((
                            max(0, x - mx), max(0, y - my),
                            min(img.width, x + w + mx),
                            min(img.height, y + h + my)
                        )).resize((48, 48))
                        arr = np.array(crop)
                        qimg = QImage(arr.data, 48, 48, 3 * 48,
                                      QImage.Format_RGB888)
                        item.setIcon(QIcon(QPixmap.fromImage(qimg)))
            except Exception:
                pass
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        # Modo de borrado
        from PyQt5.QtWidgets import QCheckBox
        chk_full = QCheckBox(
            "Eliminar registro completo\n"
            "(los rostros quedarán sin asignar para el próximo clustering)"
        )
        layout.addWidget(chk_full)

        info = QLabel("Sin marcar: solo se borra el nombre, "
                      "la agrupación de rostros se conserva.")
        info.setStyleSheet("color:#666; font-size:9pt;")
        layout.addWidget(info)

        btn_apply = QPushButton("Aplicar")
        btn_apply.setStyleSheet(
            "QPushButton{background:#c42b1c;color:white;padding:8px;"
            "border-radius:4px;font-weight:bold;}"
            "QPushButton:hover{background:#a01010;}"
        )
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(dlg.reject)

        row_btns = QHBoxLayout()
        row_btns.addWidget(btn_apply)
        row_btns.addWidget(btn_cancel)
        layout.addLayout(row_btns)

        def do_apply():
            selected = list_widget.selectedItems()
            if not selected:
                QMessageBox.information(dlg, "Sin selección",
                                        "No has seleccionado ninguna persona.")
                return

            full = chk_full.isChecked()
            confirm = QMessageBox.question(
                dlg, "Confirmar",
                f"Se va a {'eliminar completamente' if full else 'borrar el nombre de'} "
                f"{len(selected)} persona(s). ¿Continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

            conn = self.db.connect()
            for item in selected:
                pid = item.data(Qt.UserRole)
                if full:
                    conn.execute(
                        "UPDATE faces SET person_id = NULL WHERE person_id = ?",
                        (pid,)
                    )
                    conn.execute("DELETE FROM persons WHERE id = ?", (pid,))
                else:
                    conn.execute(
                        "UPDATE persons SET name = NULL WHERE id = ?", (pid,)
                    )
            conn.commit()

            self.load_persons()
            self.load_statistics()
            verbo = "eliminadas" if full else "nombre borrado"
            self.status_bar.showMessage(
                f"{len(selected)} persona(s) — {verbo}"
            )
            QMessageBox.information(dlg, "Completado",
                                    f"Se procesaron {len(selected)} persona(s).")
            dlg.accept()

        btn_apply.clicked.connect(do_apply)
        dlg.exec_()
    # ==================== MÉTODOS AUXILIARES ====================
    
    def show_about(self):
        """Muestra información de la aplicación"""
        QMessageBox.about(
            self,
            "Acerca de PTITU",
            "<h2>PTITU - Organizador de Fotografías</h2>"
            "<p>Versión 1.0</p>"
            "<p>Sistema de organización automática de colecciones fotográficas "
            "mediante reconocimiento facial y análisis de metadatos.</p>"
            "<p><b>Tecnologías:</b></p>"
            "<ul>"
            "<li>Python 3.10</li>"
            "<li>PyQt5</li>"
            "<li>TensorFlow + MTCNN</li>"
            "<li>FaceNet</li>"
            "<li>DBSCAN Clustering</li>"
            "<li>ResNet50 para escenas</li>"
            "</ul>"
        )
    
 

# ==================== MÉTODOS AUXILIARES ====================

    def show_about(self):
        """Muestra información de la aplicación"""
        QMessageBox.about(
            self,
            "Acerca de PTITU",
            "<h2>PTITU - Organizador de Fotografías</h2>"
            "<p>Versión 1.0</p>"
            "<p>Sistema de organización automática de colecciones fotográficas "
            "mediante reconocimiento facial y análisis de metadatos.</p>"
            "<p><b>Tecnologías:</b></p>"
            "<ul>"
            "<li>Python 3.10</li>"
            "<li>PyQt5</li>"
            "<li>TensorFlow + MTCNN</li>"
            "<li>FaceNet</li>"
            "<li>DBSCAN Clustering</li>"
            "<li>ResNet50 para escenas</li>"
            "</ul>"
        )

def closeEvent(self, event):
        """Maneja el cierre de la aplicación"""
        self.db.close()
        event.accept()