"""
Modelo de datos para escenas clasificadas
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Scene:
    """Representa una escena clasificada en una fotografía"""
    
    id: Optional[int] = None
    photo_id: Optional[int] = None
    category: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'photo_id': self.photo_id,
            'category': self.category,
            'confidence': self.confidence
        }
    
    def get_category_display(self) -> str:
        """Retorna el nombre de categoría formateado para mostrar"""
        return self.category.replace('_', ' ').title()