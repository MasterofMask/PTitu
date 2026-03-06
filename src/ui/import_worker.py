"""
Worker thread para importación de fotos.

Ejecuta el proceso en segundo plano para no bloquear la UI.
La deduplicación se realiza por hash MD5 del contenido del archivo,
por lo que reimportar la misma carpeta no genera duplicados.
"""
import logging
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from src.core.database import DatabaseManager
from src.processors.metadata_processor import MetadataProcessor
from src.processors.face_processor import FaceProcessor
from src.models.photo import Photo

logger = logging.getLogger(__name__)


class ImportWorker(QThread):
    """Thread para importar fotos sin bloquear la UI"""

    progress = pyqtSignal(int)    # Progreso 0-100
    status   = pyqtSignal(str)    # Mensaje de estado
    finished = pyqtSignal(dict)   # Resultados finales
    error    = pyqtSignal(str)    # Mensaje de error

    def __init__(self, folder_path: Path, process_faces: bool = True):
        super().__init__()
        self.folder_path   = folder_path
        self.process_faces = process_faces
        self.is_running    = True

    def run(self):
        """Ejecuta la importación completa"""
        try:
            db                 = DatabaseManager()
            metadata_processor = MetadataProcessor()

            # ── Inicializar clasificador de escenas ─────────────────
            self.status.emit("Inicializando clasificador de escenas...")
            from src.processors.scene_processor import SceneProcessor
            from src.core.config import MODELS_DIR
            scene_processor = SceneProcessor(
                weights_path=MODELS_DIR / 'vgg16_scene_classifier.pth'
            )

            # ── Inicializar detector de rostros ─────────────────────
            face_processor = None
            if self.process_faces:
                self.status.emit("Inicializando detector de rostros...")
                face_processor = FaceProcessor()
                self.status.emit("✓ Detector de rostros inicializado")

            # ── Buscar archivos de imagen ───────────────────────────
            self.status.emit("Buscando imágenes...")
            from src.core.config import SUPPORTED_FORMATS

            image_files = []
            for ext in SUPPORTED_FORMATS:
                image_files.extend(self.folder_path.rglob(f"*{ext}"))
                image_files.extend(self.folder_path.rglob(f"*{ext.upper()}"))

            # Eliminar rutas duplicadas dentro del mismo escaneo
            image_files = list({str(p): p for p in image_files}.values())

            if not image_files:
                self.error.emit("No se encontraron imágenes en la carpeta")
                return

            total_files      = len(image_files)
            imported         = 0   # fotos realmente nuevas
            skipped          = 0   # duplicados ignorados
            errors           = 0
            total_faces      = 0
            scenes_classified = 0

            self.status.emit(f"Procesando {total_files} imágenes...")

            # ── Procesar cada imagen ────────────────────────────────
            for i, image_file in enumerate(image_files):
                if not self.is_running:
                    self.status.emit("Importación cancelada por el usuario")
                    break

                progress = int((i / total_files) * 90)
                self.progress.emit(progress)
                self.status.emit(
                    f"Procesando ({i + 1}/{total_files}): {image_file.name}"
                )

                try:
                    # Crear objeto Photo (calcula hash MD5 aquí)
                    photo = Photo.from_file(image_file)

                    # Verificar duplicado por contenido ANTES de procesar
                    if photo.file_hash and db.photo_exists_by_hash(photo.file_hash):
                        logger.debug(f"Duplicado omitido: {image_file.name}")
                        skipped += 1
                        continue

                    # Extraer metadatos EXIF
                    metadata = metadata_processor.process_file(image_file)
                    if metadata.get('timestamp'):
                        photo.timestamp = metadata['timestamp']

                    # Insertar en base de datos
                    photo_id = db.insert_photo(photo.to_dict())

                    # insert_photo devuelve None si colisión inesperada
                    if photo_id is None:
                        skipped += 1
                        continue

                    # Insertar metadatos EXIF
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
                        logger.warning(
                            f"Error clasificando escena para {image_file.name}: {e}"
                        )

                    # Detectar y guardar rostros
                    if self.process_faces and face_processor:
                        try:
                            faces = face_processor.process_image(image_file)
                            for face in faces:
                                face['photo_id'] = photo_id
                                db.insert_face(face)
                                total_faces += 1
                        except Exception as e:
                            logger.warning(
                                f"Error detectando rostros en {image_file.name}: {e}"
                            )

                    db.update_photo_processed(photo_id)
                    imported += 1

                except Exception as e:
                    errors += 1
                    msg = f"Error con {image_file.name}: {str(e)}"
                    self.status.emit(msg)
                    logger.error(msg)
                    continue

            # ── Clustering facial (90-100 %) ────────────────────────
            n_persons = 0
            if self.process_faces and total_faces > 0:
                self.status.emit("Agrupando personas detectadas...")
                self.progress.emit(92)
                try:
                    from src.clustering.face_clustering import FaceClustering
                    clusterer  = FaceClustering()
                    clusterer.cluster_from_database(db)
                    stats_cl   = clusterer.get_cluster_statistics()
                    n_persons  = stats_cl['n_clusters']
                    self.status.emit(f"✓ Identificadas {n_persons} persona(s)")
                except Exception as e:
                    logger.error(f"Error durante clustering: {e}")

            # ── Finalizar ───────────────────────────────────────────
            self.progress.emit(100)

            if skipped > 0:
                self.status.emit(
                    f"Importación completada — {skipped} foto(s) ya existían, omitidas"
                )
            else:
                self.status.emit("Importación completada")

            self.finished.emit({
                'imported':          imported,
                'skipped':           skipped,
                'errors':            errors,
                'total_faces':       total_faces,
                'n_persons':         n_persons,
                'total_files':       total_files,
                'scenes_classified': scenes_classified,
            })

            db.close()

        except Exception as e:
            msg = f"Error durante la importación: {str(e)}"
            logger.error(msg)
            import traceback
            traceback.print_exc()
            self.error.emit(msg)

    def stop(self):
        """Solicita la detención del worker"""
        self.is_running = False