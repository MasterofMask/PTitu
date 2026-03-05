"""
Módulo de exportación de fotografías organizadas por escena.

Exporta las fotografías clasificadas hacia una carpeta destino
organizándolas en subcarpetas por categoría de escena.

Estructura generada:
    destino/
    ├── interiores/
    ├── exteriores/
    ├── restaurantes/
    ├── eventos_sociales/
    ├── actividades_deportivas/
    └── sin_clasificar/
"""
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional, Callable

from src.core.database import DatabaseManager
from src.core.config import SCENE_CATEGORIES

logger = logging.getLogger(__name__)

# Emojis para cada categoría (usados en nombres de carpeta)
CATEGORY_LABELS: Dict[str, str] = {
    'interiores':              'Interiores',
    'exteriores':              'Exteriores',
    'restaurantes':            'Restaurantes',
    'eventos_sociales':        'Eventos_Sociales',
    'actividades_deportivas':  'Actividades_Deportivas',
}


class PhotoExporter:
    """
    Exporta fotografías organizadas por categoría de escena.

    Copia las fotos originales (sin modificarlas) hacia subcarpetas
    dentro del directorio destino elegido por el usuario.
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        Inicializa el exportador.

        Args:
            db: Instancia de DatabaseManager. Si es None se crea una nueva.
        """
        self.db = db or DatabaseManager()

    def export_by_scene(
        self,
        dest_dir: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, int]:
        """
        Exporta todas las fotos clasificadas hacia dest_dir/por_escena/.

        Fotos sin clasificación se copian a la subcarpeta 'sin_clasificar'.
        Los archivos con el mismo nombre en destino se renombran
        automáticamente añadiendo un sufijo numérico.

        Args:
            dest_dir:          Ruta base de exportación elegida por el usuario.
            progress_callback: Función opcional (porcentaje, mensaje) para
                               reportar progreso en tiempo real.

        Returns:
            Diccionario {categoria: n_fotos_copiadas}.
        """
        export_root = dest_dir / 'por_escena'

        # ── Crear subcarpetas ─────────────────────────────────────────────────
        all_folders = list(CATEGORY_LABELS.values()) + ['Sin_Clasificar']
        for folder in all_folders:
            (export_root / folder).mkdir(parents=True, exist_ok=True)

        # ── Obtener todas las fotos de la BD ──────────────────────────────────
        all_photos = self.db.get_all_photos()
        if not all_photos:
            logger.warning("No hay fotografías en la base de datos para exportar")
            return {}

        total      = len(all_photos)
        counts: Dict[str, int] = {f: 0 for f in all_folders}
        errors     = 0

        for i, photo in enumerate(all_photos):
            # Progreso
            pct = int((i / total) * 100)
            if progress_callback:
                progress_callback(pct, f"Exportando ({i+1}/{total}): {photo['file_name']}")

            src_path = Path(photo['file_path'])
            if not src_path.exists():
                logger.warning(f"Archivo no encontrado: {src_path}")
                errors += 1
                continue

            # ── Determinar categoría ──────────────────────────────────────────
            scene = self.db.get_scene(photo['id'])
            if scene and scene.get('category') in CATEGORY_LABELS:
                folder_name = CATEGORY_LABELS[scene['category']]
            else:
                folder_name = 'Sin_Clasificar'

            # ── Copiar evitando colisiones de nombre ──────────────────────────
            dest_path = self._unique_path(export_root / folder_name, src_path.name)
            try:
                shutil.copy2(src_path, dest_path)
                counts[folder_name] += 1
                logger.debug(f"Copiado: {src_path.name} → {folder_name}/")
            except Exception as e:
                logger.error(f"Error copiando {src_path.name}: {e}")
                errors += 1

        if progress_callback:
            progress_callback(100, "Exportación completada")

        if errors:
            logger.warning(f"Exportación terminó con {errors} errores")

        logger.info(f"Exportación completada: {sum(counts.values())} fotos → {export_root}")
        return counts

    @staticmethod
    def _unique_path(directory: Path, filename: str) -> Path:
        """
        Genera una ruta única dentro de directory para filename.

        Si 'foto.jpg' ya existe, devuelve 'foto_1.jpg', 'foto_2.jpg', etc.

        Args:
            directory: Carpeta destino.
            filename:  Nombre de archivo original.

        Returns:
            Path que no colisiona con archivos existentes.
        """
        dest = directory / filename
        if not dest.exists():
            return dest

        stem   = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while True:
            dest = directory / f"{stem}_{counter}{suffix}"
            if not dest.exists():
                return dest
            counter += 1

    def get_export_summary(self, dest_dir: Path) -> Dict[str, int]:
        """
        Cuenta cuántas fotos hay en cada subcarpeta de una exportación previa.

        Args:
            dest_dir: Misma ruta base usada en export_by_scene().

        Returns:
            Diccionario {carpeta: n_archivos}.
        """
        export_root = dest_dir / 'por_escena'
        summary: Dict[str, int] = {}
        if not export_root.exists():
            return summary

        for folder in export_root.iterdir():
            if folder.is_dir():
                n = len([
                    f for f in folder.iterdir()
                    if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.tiff'}
                ])
                summary[folder.name] = n

        return summary