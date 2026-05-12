# -*- mode: python ; coding: utf-8 -*-
"""
PTitu.spec — Configuración de PyInstaller para PTitu.

Notas importantes:
  - Usa facenet_pytorch.MTCNN (sin TensorFlow)
  - Modelo VGG-16 se incluye como archivo de datos
  - Compatible con Python 3.10 / Windows 11 64-bit

Uso:
    pyinstaller PTitu.spec --clean --noconfirm
    # O bien:
    python build.py --only-exe
"""
from pathlib import Path
import torch
import torchvision

ROOT     = Path(SPECPATH)
SRC      = ROOT / 'src'
DATA_DIR = ROOT / 'data'

# ── Archivos de datos a incluir en el bundle ──────────────────────────────
added_datas = [
    # Iconos de la UI
    (str(SRC / 'ui' / 'icons'),   'src/ui/icons'),

    # Modelo VGG-16 entrenado
    (str(DATA_DIR / 'models' / 'vgg16_scene_classifier.pth'), 'data/models'),
    (str(DATA_DIR / 'models' / 'training_history.json'),      'data/models'),

    # Runtime de PyTorch (necesario para que funcione en cualquier PC)
    (str(Path(torch.__file__).parent),       'torch'),
    (str(Path(torchvision.__file__).parent), 'torchvision'),
]

# ── Importaciones ocultas (PyInstaller no las detecta automáticamente) ────
hidden_imports = [
    # PyQt5
    'PyQt5.QtSvg', 'PyQt5.QtXml', 'PyQt5.sip', 'PyQt5.QtCore',
    'PyQt5.QtGui', 'PyQt5.QtWidgets',

    # PyTorch y torchvision
    'torch', 'torch.nn', 'torch.nn.functional', 'torch.utils',
    'torch.utils.data', 'torch.jit', 'torch.hub',
    'torchvision', 'torchvision.models', 'torchvision.transforms',
    'torchvision.models.vgg',

    # FaceNet-PyTorch (MTCNN + InceptionResnetV1, sin TensorFlow)
    'facenet_pytorch',
    'facenet_pytorch.models',
    'facenet_pytorch.models.inception_resnet_v1',
    'facenet_pytorch.models.mtcnn',
    'facenet_pytorch.models.utils',

    # Scikit-learn y scipy
    'sklearn', 'sklearn.cluster', 'sklearn.cluster._dbscan_inner',
    'sklearn.metrics', 'sklearn.metrics.pairwise',
    'sklearn.utils._weight_vector',
    'scipy.spatial', 'scipy.spatial.distance',
    'scipy.spatial._ckdtree',

    # Imágenes
    'PIL', 'PIL.Image', 'PIL.ExifTags', 'PIL.ImageDraw',
    'cv2', 'skimage',

    # Metadatos
    'exifread',

    # Utilidades
    'numpy', 'numpy.core._multiarray_umath',
    'dateutil', 'dateutil.parser',
    'tqdm', 'tqdm.auto',
    'pkg_resources', 'pkg_resources.py2_compat',
    'sqlite3',
]

# ── Exclusiones para reducir tamaño del ejecutable ────────────────────────
excludes = [
    # TensorFlow NO es dependencia (usamos facenet_pytorch.MTCNN)
    'tensorflow', 'tensorflow_core', 'tensorflow_estimator', 'keras',
    'mtcnn',             # paquete mtcnn viejo (requería TensorFlow)

    # Herramientas de desarrollo
    'matplotlib', 'notebook', 'jupyter', 'IPython', 'ipykernel',
    'pytest', 'pylint', 'black', 'mypy',

    # Otras UIs
    'tkinter', '_tkinter', 'wx',

    # Datos científicos no usados
    'pandas',
]

a = Analysis(
    ['src/main.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=['.pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='organizador',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # Sin ventana de consola
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src\\ui\\icons\\ptitu.ico',
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python310.dll',
        'Qt5Core.dll',
        'Qt5Gui.dll',
        'Qt5Widgets.dll',
    ],
    name='organizador',
)
