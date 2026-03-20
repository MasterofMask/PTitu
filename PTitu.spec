# -*- mode: python ; coding: utf-8 -*-
"""
PTitu.spec — Configuración de PyInstaller para PTitu.

Uso:
    pyinstaller PTitu.spec
"""

from pathlib import Path
import torch
import torchvision

ROOT     = Path(SPECPATH)
SRC      = ROOT / 'src'
DATA_DIR = ROOT / 'data'

added_datas = [
    (str(SRC / 'ui' / 'icons'),   'src/ui/icons'),
    (str(DATA_DIR / 'models' / 'vgg16_scene_classifier.pth'), 'data/models'),
    (str(DATA_DIR / 'models' / 'training_history.json'),      'data/models'),
    (str(Path(torch.__file__).parent),       'torch'),
    (str(Path(torchvision.__file__).parent), 'torchvision'),
]

hidden_imports = [
    'PyQt5.QtSvg', 'PyQt5.QtXml', 'PyQt5.sip',
    'torch', 'torch.nn', 'torch.nn.functional',
    'torchvision', 'torchvision.models', 'torchvision.transforms',
    # MTCNN y FaceNet ambos de facenet-pytorch (sin TensorFlow)
    'facenet_pytorch', 'facenet_pytorch.models',
    'facenet_pytorch.models.inception_resnet_v1',
    'facenet_pytorch.models.mtcnn',
    'sklearn', 'sklearn.cluster', 'sklearn.metrics',
    'scipy.spatial.distance', 'scipy.spatial',
    'PIL', 'PIL.Image', 'PIL.ExifTags',
    'exifread', 'numpy', 'dateutil', 'dateutil.parser', 'tqdm',
    'pkg_resources', 'pkg_resources.py2_compat',
]

excludes = [
    # tensorflow ya no es dependencia — usamos facenet_pytorch.MTCNN
    'tensorflow', 'tensorflow_core', 'keras',
    'mtcnn',   # paquete mtcnn (el que requería TensorFlow)
    'matplotlib', 'notebook', 'jupyter', 'IPython',
    'pandas', 'skimage', 'tkinter', '_tkinter', 'wx',
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
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PTitu',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='src/ui/icons/ptitu.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PTitu',
)
