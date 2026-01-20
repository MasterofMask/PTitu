"""
Ventana principal de la aplicación
"""
import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTabWidget,
    QStatusBar, QAction, QMenuBar, QMessageBox,
    QProgressBar, QListWidget, QListWidgetItem,
    QGridLayout, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap

from src.core.database import DatabaseManager
from src.ui.styles import MAIN_STYLE


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
        
        process_action = QAction("&Procesar Fotos", self)
        process_action.triggered.connect(self.process_photos)
        tools_menu.addAction(process_action)
        
        cluster_action = QAction("&Agrupar Personas", self)
        cluster_action.triggered.connect(self.cluster_faces)
        tools_menu.addAction(cluster_action)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("&Ayuda")
        
        about_action = QAction("&Acerca de", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
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
        
        # Botón: Procesar
        btn_process = QPushButton("⚙️ Procesar Fotos")
        btn_process.setMinimumHeight(80)
        btn_process.setStyleSheet("font-size: 14pt;")
        btn_process.clicked.connect(self.process_photos)
        btn_layout.addWidget(btn_process, 1, 1)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def create_gallery_tab(self):
        """Crea la pestaña de galería"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Lista de fotos
        self.photo_list = QListWidget()
        self.photo_list.setViewMode(QListWidget.IconMode)
        self.photo_list.setIconSize(QSize(200, 200))
        self.photo_list.setResizeMode(QListWidget.Adjust)
        self.photo_list.setSpacing(10)
        
        layout.addWidget(QLabel("Todas las fotografías:"))
        layout.addWidget(self.photo_list)
        
        # Botón para recargar
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_gallery)
        layout.addWidget(btn_refresh)
        
        widget.setLayout(layout)
        return widget
    
    def create_persons_tab(self):
        """Crea la pestaña de personas"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Lista de personas
        self.persons_list = QListWidget()
        
        layout.addWidget(QLabel("Personas identificadas:"))
        layout.addWidget(self.persons_list)
        
        # Botón para recargar
        btn_refresh = QPushButton("🔄 Actualizar")
        btn_refresh.clicked.connect(self.load_persons)
        layout.addWidget(btn_refresh)
        
        widget.setLayout(layout)
        return widget
    
    def load_statistics(self):
        """Carga las estadísticas desde la base de datos"""
        stats = self.db.get_statistics()
        
        self.stats_photos.setText(str(stats['total_photos']))
        self.stats_faces.setText(str(stats['total_faces']))
        self.stats_persons.setText(str(stats['total_persons']))
    
    def load_gallery(self):
        """Carga la galería de fotos"""
        self.photo_list.clear()
        
        photos = self.db.get_all_photos(limit=100)
        
        for photo in photos:
            item = QListWidgetItem(photo['file_name'])
            
            # Intentar cargar thumbnail
            try:
                pixmap = QPixmap(photo['file_path'])
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(pixmap))
            except:
                pass
            
            self.photo_list.addItem(item)
        
        self.status_bar.showMessage(f"Cargadas {len(photos)} fotos")
    
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
    
    def import_photos(self):
        """Importa fotos desde una carpeta"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta con fotografías",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            reply = QMessageBox.question(
                self,
                "Procesar fotos",
                "¿Deseas detectar rostros automáticamente?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            process_faces = (reply == QMessageBox.Yes)
            
            QMessageBox.information(
                self,
                "Importación",
                f"Se importarán fotos desde:\n{folder}\n\n"
                f"Detección de rostros: {'Sí' if process_faces else 'No'}\n\n"
                "Esta función se implementará en la siguiente iteración."
            )
    
    def process_photos(self):
        """Procesa fotos pendientes"""
        QMessageBox.information(
            self,
            "Procesar Fotos",
            "Esta función procesará las fotos pendientes.\n"
            "Se implementará en la siguiente iteración."
        )
    
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
            "</ul>"
        )
    
    def closeEvent(self, event):
        """Maneja el cierre de la aplicación"""
        self.db.close()
        event.accept()