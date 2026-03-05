"""
Configuración global de la aplicación
"""
import os
from pathlib import Path

# Directorios base
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
MODELS_DIR = DATA_DIR / 'models'

# Base de datos
DATABASE_PATH = DATA_DIR / 'database.db'

# Procesamiento de imágenes
MIN_IMAGE_RESOLUTION = (640, 480)
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.tiff']

# Clustering facial
FACE_EMBEDDING_SIZE = 512  # FaceNet genera embeddings de 512 dimensiones
FACE_CONFIDENCE_THRESHOLD = 0.9
DBSCAN_EPS = 0.6
DBSCAN_MIN_SAMPLES = 2

# Reconocimiento de escenas
SCENE_CATEGORIES = [
    'actividades_deportivas',
    'eventos_sociales',
    'exteriores',
    'interiores',
    'restaurantes'
]
SCENE_CONFIDENCE_THRESHOLD = 0.55

# Clustering temporal
TEMPORAL_MIN_THRESHOLD = 300  # 5 minutos en segundos
TEMPORAL_MAX_THRESHOLD = 86400  # 24 horas en segundos
TEMPORAL_SCALE = 3600  # 1 hora en segundos

# Interfaz de usuario
THUMBNAIL_SIZE = (200, 200)
BATCH_SIZE = 32

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Crear directorios si no existen
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
