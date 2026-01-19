"""
Modelo de datos para fotografías
"""
from dataclasses import dataclass
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
    
    @classmethod
    def from_file(cls, file_path: Path) -> 'Photo':
        """
        Crea una instancia de Photo desde un archivo.
        
        Args:
            file_path: Ruta al archivo de imagen
            
        Returns:
            Instancia de Photo con datos básicos
        """
        stat = file_path.stat()
        
        # Obtener dimensiones usando PIL
        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception:
            width, height = 0, 0
        
        return cls(
            file_path=str(file_path.absolute()),
            file_name=file_path.name,
            file_size=stat.st_size,
            width=width,
            height=height,
            format=file_path.suffix.lower()
        )
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'width': self.width,
            'height': self.height,
            'format': self.format,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'processed': self.processed
        }
    
    def get_path(self) -> Path:
        """Retorna la ruta como objeto Path"""
        return Path(self.file_path)


@dataclass
class PhotoMetadata:
    """Metadatos EXIF de una fotografía"""
    
    id: Optional[int] = None
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
    
    def has_gps(self) -> bool:
        """Verifica si tiene datos GPS válidos"""
        return (self.gps_latitude is not None and 
                self.gps_longitude is not None)
    
    def get_coordinates(self) -> Optional[tuple]:
        """Retorna coordenadas GPS como tupla (lat, lon)"""
        if self.has_gps():
            return (self.gps_latitude, self.gps_longitude)
        return None
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'photo_id': self.photo_id,
            'camera_make': self.camera_make,
            'camera_model': self.camera_model,
            'focal_length': self.focal_length,
            'aperture': self.aperture,
            'exposure_time': self.exposure_time,
            'iso': self.iso,
            'flash': self.flash,
            'gps_latitude': self.gps_latitude,
            'gps_longitude': self.gps_longitude,
            'gps_altitude': self.gps_altitude
        }