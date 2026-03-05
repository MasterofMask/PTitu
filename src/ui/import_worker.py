"""
Worker thread para importación de fotos
"""
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import List

from src.core.database import DatabaseManager
from src.processors.metadata_processor import MetadataProcessor
from src.processors.face_processor import FaceProcessor
from src.models.photo import Photo


class ImportWorker(QThread):
    """Thread para importar fotos sin bloquear la UI"""
    
    # Señales
    progress = pyqtSignal(int)  # Progreso (0-100)
    status = pyqtSignal(str)    # Mensaje de estado
    finished = pyqtSignal(dict)  # Resultados finales
    error = pyqtSignal(str)     # Error
    
    def __init__(self, folder_path: Path, process_faces: bool = True):
        super().__init__()
        self.folder_path = folder_path
        self.process_faces = process_faces
        self.is_running = True
    
    """
Worker thread para importación de fotos
"""
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from typing import List
import logging

from src.core.database import DatabaseManager
from src.processors.metadata_processor import MetadataProcessor
from src.processors.face_processor import FaceProcessor
from src.models.photo import Photo

logger = logging.getLogger(__name__)


class ImportWorker(QThread):
    """Thread para importar fotos sin bloquear la UI"""
    
    # Señales
    progress = pyqtSignal(int)  # Progreso (0-100)
    status = pyqtSignal(str)    # Mensaje de estado
    finished = pyqtSignal(dict)  # Resultados finales
    error = pyqtSignal(str)     # Error
    
    def __init__(self, folder_path: Path, process_faces: bool = True):
        super().__init__()
        self.folder_path = folder_path
        self.process_faces = process_faces
        self.is_running = True
    
    def run(self):
        """Ejecuta la importación"""
        try:
            # Inicializar componentes
            db = DatabaseManager()
            metadata_processor = MetadataProcessor()
            
            # Inicializar procesador de escenas
            self.status.emit("Inicializando clasificador de escenas...")
            from src.processors.scene_processor import SceneProcessor
            from src.core.config import MODELS_DIR
            scene_processor = SceneProcessor(
                weights_path=MODELS_DIR / 'vgg16_scene_classifier.pth'
            )
            
            face_processor = None
            if self.process_faces:
                self.status.emit("Inicializando detector de rostros...")
                face_processor = FaceProcessor()
                self.status.emit("✓ Detector de rostros inicializado")
            
            # Buscar archivos de imagen
            self.status.emit("Buscando imágenes...")
            from src.core.config import SUPPORTED_FORMATS
            
            image_files = []
            for ext in SUPPORTED_FORMATS:
                image_files.extend(self.folder_path.rglob(f"*{ext}"))
                image_files.extend(self.folder_path.rglob(f"*{ext.upper()}"))
            
            if not image_files:
                self.error.emit("No se encontraron imágenes en la carpeta")
                return
            
            total_files = len(image_files)
            imported = 0
            errors = 0
            total_faces = 0
            scenes_classified = 0
            
            # Procesar cada imagen
            self.status.emit(f"Procesando {total_files} imágenes...")
            
            for i, image_file in enumerate(image_files):
                if not self.is_running:
                    self.status.emit("Importación cancelada por el usuario")
                    break
                
                try:
                    # Actualizar progreso (0-90% para procesamiento de imágenes)
                    progress = int((i / total_files) * 90)
                    self.progress.emit(progress)
                    self.status.emit(f"Procesando ({i+1}/{total_files}): {image_file.name}")
                    
                    # Crear objeto Photo
                    photo = Photo.from_file(image_file)
                    
                    # Extraer metadatos
                    metadata = metadata_processor.process_file(image_file)
                    if metadata.get('timestamp'):
                        photo.timestamp = metadata['timestamp']
                    
                    # Insertar en base de datos
                    photo_id = db.insert_photo(photo.to_dict())
                    
                    # Insertar metadatos si existen
                    if metadata:
                        db.insert_metadata(photo_id, metadata)
                    
                    # Clasificar escena
                    try:
                        scene_result = scene_processor.process_image(image_file)
                        if scene_result['confidence'] >= 0.55:
                            db.insert_scene(
                                photo_id,
                                scene_result['category'],
                                scene_result['confidence']
                            )
                            scenes_classified += 1
                    except Exception as e:
                        logger.warning(f"Error clasificando escena para {image_file.name}: {e}")
                    
                    # Procesar rostros si está habilitado
                    if self.process_faces and face_processor:
                        try:
                            faces = face_processor.process_image(image_file)
                            
                            for face in faces:
                                face['photo_id'] = photo_id
                                db.insert_face(face)
                                total_faces += 1
                        except Exception as e:
                            logger.warning(f"Error detectando rostros en {image_file.name}: {e}")
                    
                    # Marcar como procesada
                    db.update_photo_processed(photo_id)
                    
                    imported += 1
                    
                except Exception as e:
                    errors += 1
                    error_msg = f"Error con {image_file.name}: {str(e)}"
                    self.status.emit(error_msg)
                    logger.error(error_msg)
                    continue
            
            # Ejecutar clustering si hay rostros (90-100% del progreso)
            if self.process_faces and total_faces > 0:
                self.status.emit("Agrupando personas detectadas...")
                self.progress.emit(92)
                
                try:
                    from src.clustering.face_clustering import FaceClustering
                    
                    clusterer = FaceClustering()
                    clusters = clusterer.cluster_from_database(db)
                    
                    stats_clustering = clusterer.get_cluster_statistics()
                    n_persons = stats_clustering['n_clusters']
                    
                    self.status.emit(f"✓ Identificadas {n_persons} persona(s)")
                except Exception as e:
                    logger.error(f"Error durante clustering: {e}")
                    n_persons = 0
            else:
                n_persons = 0
            
            # Completado
            self.progress.emit(100)
            self.status.emit("Importación completada")
            
            results = {
                'imported': imported,
                'errors': errors,
                'total_faces': total_faces,
                'n_persons': n_persons,
                'total_files': total_files,
                'scenes_classified': scenes_classified
            }
            
            self.finished.emit(results)
            
            db.close()
            
        except Exception as e:
            error_msg = f"Error durante la importación: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            self.error.emit(error_msg)
    
    def stop(self):
        """Detiene el worker"""
        self.is_running = False