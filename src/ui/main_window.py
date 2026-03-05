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
    QDialog, QComboBox, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap

from src.core.database import DatabaseManager
from src.ui.styles import MAIN_STYLE

logger = logging.getLogger(__name__)


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
        tools_menu = menubar.addMenu("&Herramientas")
        
        cluster_action = QAction("&Agrupar Personas", self)
        cluster_action.triggered.connect(self.cluster_faces)
        tools_menu.addAction(cluster_action)
        
        tools_menu.addSeparator()
        
        clean_action = QAction("🧹 &Limpiar Duplicados", self)
        clean_action.triggered.connect(self.clean_duplicates)
        tools_menu.addAction(clean_action)
        
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
        self.scene_filter.addItem("🏖️ Playa", "playa")
        self.scene_filter.addItem("🍽️ Restaurante", "restaurante")
        self.scene_filter.addItem("🌳 Exterior", "exterior")
        self.scene_filter.addItem("🏠 Interior", "interior")
        self.scene_filter.addItem("⚽ Evento Deportivo", "evento_deportivo")
        self.scene_filter.addItem("🎉 Evento Social", "evento_social")
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
        """Crea la pestaña de personas"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Buscador
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Buscar:"))
        
        self.person_search = QLineEdit()
        self.person_search.setPlaceholderText("Escribe un nombre para buscar...")
        self.person_search.textChanged.connect(self.filter_persons)
        search_layout.addWidget(self.person_search)
        
        layout.addLayout(search_layout)
        
        # Lista de personas
        self.persons_list = QListWidget()
        self.persons_list.itemDoubleClicked.connect(self.rename_person)
        
        layout.addWidget(QLabel("Personas identificadas:"))
        layout.addWidget(self.persons_list)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        # Botón para renombrar
        btn_rename = QPushButton("✏️ Renombrar")
        btn_rename.clicked.connect(self.rename_selected_person)
        btn_layout.addWidget(btn_rename)
        
        # Botón para ver fotos
        btn_view = QPushButton("👁️ Ver Fotos")
        btn_view.clicked.connect(self.view_person_photos)
        btn_layout.addWidget(btn_view)
        
        # Botón para actualizar
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_persons)
        btn_layout.addWidget(btn_refresh)
        
        layout.addLayout(btn_layout)
        
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
        """Carga la lista de personas"""
        self.persons_list.clear()
        
        persons = self.db.get_all_persons()
        
        for person in persons:
            name = person['name'] or f"Persona {person['cluster_id']}"
            count = person['photo_count']
            
            item = QListWidgetItem(f"{name} - {count} foto(s)")
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
        """Renombra la persona seleccionada"""
        current_item = self.persons_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Por favor, selecciona una persona de la lista."
            )
            return
        
        # Extraer información de la persona
        text = current_item.text()
        
        # Obtener todas las personas
        persons = self.db.get_all_persons()
        
        # Encontrar la persona correspondiente
        selected_person = None
        for person in persons:
            display_name = person['name'] or f"Persona {person['cluster_id']}"
            if text.startswith(display_name):
                selected_person = person
                break
        
        if not selected_person:
            QMessageBox.warning(self, "Error", "No se pudo identificar la persona seleccionada.")
            return
        
        # Solicitar nuevo nombre
        current_name = selected_person['name'] or f"Persona {selected_person['cluster_id']}"
        
        new_name, ok = QInputDialog.getText(
            self,
            "Renombrar Persona",
            f"Ingresa un nombre para '{current_name}':",
            text=current_name
        )
        
        if ok and new_name.strip():
            # Actualizar en la base de datos
            self.db.update_person_name(selected_person['id'], new_name.strip())
            
            # Recargar lista
            self.load_persons()
            self.load_statistics()
            
            self.status_bar.showMessage(f"Persona renombrada a '{new_name.strip()}'")
            
            QMessageBox.information(
                self,
                "Éxito",
                f"La persona ha sido renombrada a:\n{new_name.strip()}"
            )
    
    def view_person_photos(self):
        """Muestra las fotos de la persona seleccionada"""
        current_item = self.persons_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Por favor, selecciona una persona de la lista."
            )
            return
        
        # Extraer información de la persona
        text = current_item.text()
        
        # Obtener todas las personas
        persons = self.db.get_all_persons()
        
        # Encontrar la persona correspondiente
        selected_person = None
        for person in persons:
            display_name = person['name'] or f"Persona {person['cluster_id']}"
            if text.startswith(display_name):
                selected_person = person
                break
        
        if not selected_person:
            QMessageBox.warning(self, "Error", "No se pudo identificar la persona seleccionada.")
            return
        
        # Obtener fotos de esta persona
        photos = self.db.search_photos(person_id=selected_person['id'])
        
        if not photos:
            QMessageBox.information(
                self,
                "Sin fotos",
                f"No se encontraron fotos de {selected_person['name'] or 'esta persona'}."
            )
            return
        
        # Crear diálogo con galería
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Fotos de {selected_person['name'] or 'Persona ' + str(selected_person['cluster_id'])}")
        dialog.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # Área de scroll
        scroll = QScrollArea()
        scroll_widget = QWidget()
        grid_layout = QGridLayout()
        
        # Añadir fotos en grid
        row, col = 0, 0
        max_cols = 3
        
        for photo in photos:
            try:
                pixmap = QPixmap(photo['file_path'])
                if not pixmap.isNull():
                    # Crear label con la imagen
                    label = QLabel()
                    pixmap = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    label.setPixmap(pixmap)
                    label.setAlignment(Qt.AlignCenter)
                    
                    # Añadir al grid
                    grid_layout.addWidget(label, row, col)
                    
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
            except:
                pass
        
        scroll_widget.setLayout(grid_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        
        layout.addWidget(QLabel(f"Mostrando {len(photos)} foto(s)"))
        layout.addWidget(scroll)
        
        # Botón cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
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
        # Ocultar barra de progreso
        self.progress_bar.setVisible(False)
        
        # Habilitar UI
        self.setEnabled(True)
        
        # Mostrar resultados
        message = (
            f"Importación completada:\n\n"
            f"✓ Fotos importadas: {results['imported']}/{results['total_files']}\n"
            f"✓ Rostros detectados: {results['total_faces']}\n"
            f"✓ Personas identificadas: {results['n_persons']}\n"
            f"✓ Escenas clasificadas: {results.get('scenes_classified', 0)}\n"
        )
        
        if results['errors'] > 0:
            message += f"\n⚠ Errores: {results['errors']}"
        
        QMessageBox.information(
            self,
            "Importación Completada",
            message
        )
        
        # Actualizar estadísticas y vistas
        self.load_statistics()
        self.load_gallery()
        self.load_persons()
        
        self.status_bar.showMessage("Listo")
    
    def on_import_error(self, error_message):
        """Maneja errores durante la importación"""
        self.progress_bar.setVisible(False)
        self.setEnabled(True)

        QMessageBox.critical(self,"Error de Importación",f"Ocurrió un error durante la importación:\n\n{error_message}")

        self.status_bar.showMessage("Error en importación")


# ==================== MÉTODOS DE EXPORTACIÓN ====================



"""
1. En los imports al inicio del archivo agrega:
       from src.exporters.export_worker import ExportWorker

2. En create_home_tab() (donde están los botones principales),
   agrega el botón de exportación dentro del btn_layout:

       btn_export = QPushButton("Exportar por Escena")
       btn_export.setMinimumHeight(80)
       btn_export.setStyleSheet("font-size: 14pt;")
       btn_export.clicked.connect(self.export_by_scene)
       btn_layout.addWidget(btn_export, 2, 0)   # ajusta fila/columna según tu layout

3. Pega los métodos de abajo dentro de la clase MainWindow.

4. En create_gallery_tab(), actualiza el filtro de escenas para
   que coincida con las categorías actuales (reemplaza los addItem
   con las líneas del método update_scene_filter que aparece abajo).
"""

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
            "No hay fotografías con escena clasificada.\n\n"
            "Importa y procesa fotos primero desde la pestaña principal.",
        )
        return

    # Seleccionar carpeta destino
    dest = QFileDialog.getExistingDirectory(
        self,
        "Seleccionar carpeta destino para exportación",
        str(Path.home()),
    )
    if not dest:
        return

    dest_path = Path(dest)

    # Mostrar resumen antes de exportar
    summary_lines = "\n".join(
        f"  • {cat}: {n} fotos" for cat, n in scenes.items()
    )
    reply = QMessageBox.question(
        self,
        "Confirmar exportación",
        f"Se exportarán {total_classified} fotos hacia:\n"
        f"{dest_path / 'por_escena'}\n\n"
        f"Distribución:\n{summary_lines}\n\n"
        "Las fotos originales NO se moverán ni eliminarán.\n"
        "¿Continuar?",
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return

    # Iniciar exportación en hilo separado
    self._start_export(dest_path)


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
    """
    Actualiza el combo de filtro de escenas en la galería con las
    categorías actuales del proyecto.

    Reemplaza el bloque de addItem existente en create_gallery_tab()
    con esta lista:
    """
    # Reemplaza los addItem del scene_filter con estos:
    self.scene_filter.clear()
    self.scene_filter.addItem("Todas",                    None)
    self.scene_filter.addItem(" Interiores",            "interiores")
    self.scene_filter.addItem("Exteriores",            "exteriores")
    self.scene_filter.addItem(" Restaurantes",          "restaurantes")
    self.scene_filter.addItem(" Eventos Sociales",      "eventos_sociales")
    self.scene_filter.addItem(" Actividades Deportivas","actividades_deportivas")




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