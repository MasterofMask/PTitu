"""
setup_icons.py — Descarga los iconos Feather Icons necesarios para la UI.

Feather Icons: MIT License — https://feathericons.com
Fuente: GitHub raw de feathericons/feather

Uso:
    python setup_icons.py

Crea la carpeta src/ui/icons/ con los SVGs necesarios.
Solo necesitas ejecutar este script UNA VEZ.
"""
import sys
import urllib.request
from pathlib import Path

# Carpeta destino
ICONS_DIR = Path(__file__).parent / "src" / "ui" / "icons"

# URL base de Feather Icons en GitHub
BASE_URL = "https://raw.githubusercontent.com/feathericons/feather/master/icons"

# Iconos necesarios para la aplicación
REQUIRED_ICONS = [
    "download.svg",   # importar fotos
    "upload-cloud.svg",     # exportar
    "image.svg",            # galería
    "users.svg",            # personas
    "trash-2.svg",          # eliminar
    "tag.svg",              # etiquetar
    "edit-2.svg",           # renombrar
    "eye.svg",              # ver detalle
    "refresh-cw.svg",       # actualizar
    "search.svg",           # buscar
    "home.svg",             # inicio
    "filter.svg",           # filtrar
    "share-2.svg",          # clustering
    "folder.svg",           # carpeta
    "check.svg",            # confirmar
    "x.svg",                # cerrar/cancelar
    "info.svg",             # información
    "alert-triangle.svg",   # advertencia
]


def download_icons():
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Descargando iconos en: {ICONS_DIR}\n")

    ok = 0
    fail = 0

    for icon_name in REQUIRED_ICONS:
        dest = ICONS_DIR / icon_name
        if dest.exists():
            print(f"  ✓ Ya existe: {icon_name}")
            ok += 1
            continue

        url = f"{BASE_URL}/{icon_name}"
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"  ↓ Descargado: {icon_name}")
            ok += 1
        except Exception as e:
            print(f"  ✗ Error: {icon_name} — {e}")
            fail += 1

    print(f"\n{'='*50}")
    print(f"✓ {ok} icono(s) listos   ✗ {fail} error(es)")

    if fail == 0:
        print("\nTodo listo. Los iconos aparecerán al reiniciar la app.")
    else:
        print("\nAlgunos iconos fallaron. Verifica tu conexión a internet.")
        print("También puedes descargarlos manualmente de https://feathericons.com")
    print(f"{'='*50}")


if __name__ == "__main__":
    download_icons()
