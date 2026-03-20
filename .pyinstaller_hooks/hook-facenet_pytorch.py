"""
.pyinstaller_hooks/hook-facenet_pytorch.py
Hook para que PyInstaller incluya todos los modelos de facenet_pytorch.
"""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('facenet_pytorch')