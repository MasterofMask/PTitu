"""
runtime_hook.py — Se ejecuta al inicio del .exe antes que cualquier otro código.
Corrige las rutas para que el programa encuentre sus archivos tanto al correr
desde código fuente como desde el ejecutable compilado.
"""
import sys
import os
from pathlib import Path

def get_base_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

base = get_base_path()
if str(base) not in sys.path:
    sys.path.insert(0, str(base))

if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).parent
    data_dir = exe_dir / 'data'
    data_dir.mkdir(exist_ok=True)
    (data_dir / 'models').mkdir(exist_ok=True)
    os.environ['PTITU_DATA_DIR'] = str(exe_dir)