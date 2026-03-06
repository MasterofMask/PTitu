"""
Modelo de datos para fotografías
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image


@dataclass
class Photo:
    """Representa una fotografía en el sistema"""

    id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    width: int = 0
    height: int = 0
    format: str = ""
    timestamp: Optional[datetime] = None
    date_added: Optional[datetime] = None
    processed: bool = False
    file_hash: Optional[str] = None   # ← hash MD5 del contenido binario

    @classmethod
    def from_file(cls, file_path: Path) -> 'Photo':
        """
        Crea una instancia de Photo desde un archivo.

        Calcula el hash MD5 del contenido para identificar duplicados
        independientemente del nombre o ubicación del archivo.

        Args:
            file_path: Ruta al archivo de imagen

        Returns:
            Instancia de Photo con metadatos básicos y hash
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        photo = cls()
        photo.file_path = str(file_path.resolve())
        photo.file_name = file_path.name
        photo.file_size = file_path.stat().st_size
        photo.format = file_path.suffix.lower()

        # Calcular hash MD5 del contenido binario
        photo.file_hash = cls._compute_hash(file_path)

        # Obtener dimensiones con PIL
        try:
            with Image.open(file_path) as img:
                photo.width, photo.height = img.size
        except Exception:
            photo.width = 0
            photo.height = 0

        return photo

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        """
        Calcula el hash MD5 del contenido del archivo.

        Se lee en bloques de 64 KB para no cargar archivos grandes
        completos en memoria.

        Args:
            file_path: Ruta al archivo

        Returns:
            Cadena hexadecimal con el hash MD5
        """
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                md5.update(chunk)
        return md5.hexdigest()

    def to_dict(self) -> dict:
        """Convierte la fotografía a diccionario para inserción en BD"""
        return {
            'file_path':  self.file_path,
            'file_name':  self.file_name,
            'file_size':  self.file_size,
            'width':      self.width,
            'height':     self.height,
            'format':     self.format,
            'timestamp':  self.timestamp,
            'file_hash':  self.file_hash,
        }


@dataclass
class PhotoMetadata:
    """Metadatos EXIF asociados a una fotografía"""

    photo_id: Optional[int] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    focal_length: Optional[float] = None
    aperture: Optional[float] = None
    exposure_time: Optional[str] = None
    iso: Optional[int] = None
    flash: Optional[int] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude: Optional[float] = None