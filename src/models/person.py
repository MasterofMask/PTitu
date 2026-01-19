"""
Modelo de datos para personas
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import numpy as np


@dataclass
class Person:
    """Representa una persona identificada en fotografías"""
    
    id: Optional[int] = None
    name: Optional[str] = None
    cluster_id: int = -1
    date_created: Optional[datetime] = None
    photo_count: int = 0
    
    def get_display_name(self) -> str:
        """Retorna el nombre para mostrar"""
        if self.name:
            return self.name
        return f"Persona {self.cluster_id}"
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.get_display_name(),
            'cluster_id': self.cluster_id,
            'date_created': self.date_created.isoformat() if self.date_created else None,
            'photo_count': self.photo_count
        }


@dataclass
class Face:
    """Representa un rostro detectado en una fotografía"""
    
    id: Optional[int] = None
    photo_id: Optional[int] = None
    person_id: Optional[int] = None
    embedding: Optional[np.ndarray] = None
    bbox_x: int = 0
    bbox_y: int = 0
    bbox_width: int = 0
    bbox_height: int = 0
    confidence: float = 0.0
    
    @property
    def bbox(self) -> tuple:
        """Retorna el bounding box como tupla (x, y, width, height)"""
        return (self.bbox_x, self.bbox_y, self.bbox_width, self.bbox_height)
    
    @property
    def bbox_xyxy(self) -> tuple:
        """Retorna el bounding box como (x1, y1, x2, y2)"""
        return (
            self.bbox_x,
            self.bbox_y,
            self.bbox_x + self.bbox_width,
            self.bbox_y + self.bbox_height
        )
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'photo_id': self.photo_id,
            'person_id': self.person_id,
            'bbox': self.bbox,
            'confidence': self.confidence
        }