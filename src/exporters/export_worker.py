"""
Worker de exportación de fotografías.

Ejecuta la exportación en un hilo separado (QThread) para no
bloquear la interfaz gráfica durante el proceso.
"""
import logging
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from src.core.database import DatabaseManager
from src.exporters.photo_exporter import PhotoExporter

logger = logging.getLogger(__name__)


class ExportWorker(QThread):
    """
    Worker que ejecuta la exportación de fotos en segundo plano.

    Signals:
        progress(int, str): Porcentaje de avance y mensaje de estado.
        finished(dict):     Resultados al completar {categoria: n_fotos}.
        error(str):         Mensaje de error si falla.
    """

    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, dest_dir: Path, parent=None):
        """
        Args:
            dest_dir: Directorio destino elegido por el usuario.
            parent:   Widget padre Qt.
        """
        super().__init__(parent)
        self.dest_dir   = dest_dir
        self.is_running = True

    def run(self):
        """Ejecuta la exportación en el hilo."""
        try:
            db       = DatabaseManager()
            exporter = PhotoExporter(db)

            counts = exporter.export_by_scene(
                self.dest_dir,
                progress_callback=self._report_progress,
            )

            db.close()
            self.finished.emit(counts)

        except Exception as e:
            logger.error(f"Error en exportación: {e}", exc_info=True)
            self.error.emit(str(e))

    def _report_progress(self, pct: int, message: str) -> None:
        """Emite señal de progreso si el worker sigue activo."""
        if self.is_running:
            self.progress.emit(pct, message)

    def stop(self):
        """Solicita detención del worker."""
        self.is_running = False