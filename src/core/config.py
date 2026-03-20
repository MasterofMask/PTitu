"""
Configuración global de la aplicación.
Detecta automáticamente si corre como script o como .exe compilado.
"""
import os, sys
from pathlib import Path


def _get_app_dir() -> Path:
    env_dir = os.environ.get('PTITU_DATA_DIR')
    if env_dir:
        return Path(env_dir)
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def _get_bundle_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


APP_DIR    = _get_app_dir()
BUNDLE_DIR = _get_bundle_dir()
BASE_DIR   = APP_DIR
DATA_DIR   = APP_DIR    / 'data'
MODELS_DIR = BUNDLE_DIR / 'data' / 'models'
DATABASE_PATH = DATA_DIR / 'database.db'

MIN_IMAGE_RESOLUTION      = (640, 480)
SUPPORTED_FORMATS         = ['.jpg', '.jpeg', '.png', '.tiff']
FACE_EMBEDDING_SIZE       = 512
FACE_CONFIDENCE_THRESHOLD = 0.9
DBSCAN_EPS                = 0.6
DBSCAN_MIN_SAMPLES        = 2
SCENE_CATEGORIES = [
    'actividades_deportivas', 'eventos_sociales',
    'exteriores', 'interiores', 'restaurantes',
]
SCENE_CONFIDENCE_THRESHOLD = 0.55
TEMPORAL_MIN_THRESHOLD = 300
TEMPORAL_MAX_THRESHOLD = 86400
TEMPORAL_SCALE         = 3600
THUMBNAIL_SIZE = (200, 200)
BATCH_SIZE     = 32
LOG_LEVEL  = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

DATA_DIR.mkdir(parents=True, exist_ok=True)