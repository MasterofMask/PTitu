#!/usr/bin/env python3
"""
build.py — Compila PTitu y genera el instalador con Inno Setup (open source).

Inno Setup es gratuito, open source (licencia BSD/MIT simplificada),
y NO es marcado como peligroso por Windows Defender a diferencia de NSIS.
  Descarga: https://jrsoftware.org/isinfo.php

Pasos automáticos:
  1. Verifica prerrequisitos
  2. Compila con PyInstaller → dist/PTitu/
  3. Genera instalador con Inno Setup → Output/PTitu_Setup_*.exe

Uso:
    python build.py                   # proceso completo
    python build.py --only-exe        # solo PyInstaller
    python build.py --only-installer  # solo Inno Setup (requiere dist/PTitu/)
    python build.py --check           # solo verificar prerrequisitos
"""
import sys
import subprocess
import shutil
import argparse
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent

# Rutas habituales del compilador de Inno Setup
ISCC_PATHS = [
    Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
    Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    Path("C:/Program Files (x86)/Inno Setup 5/ISCC.exe"),
    Path("C:/Program Files/Inno Setup 5/ISCC.exe"),
]

# Tamaño mínimo esperado del modelo VGG-16
VGG_MIN_SIZE = 10_000_000   # 10 MB


# ── Utilidades ────────────────────────────────────────────────────────────────

def run(cmd: list, check: bool = True) -> int:
    print(f"\n> {' '.join(str(c) for c in cmd)}\n")
    result = subprocess.run(cmd)
    if check and result.returncode != 0:
        print("\n✗ El comando falló. Revisa los mensajes anteriores.")
        sys.exit(1)
    return result.returncode


def find_iscc() -> Path | None:
    """Busca el compilador de Inno Setup en las rutas habituales y en PATH."""
    for p in ISCC_PATHS:
        if p.exists():
            return p
    found = shutil.which("iscc") or shutil.which("ISCC")
    return Path(found) if found else None


def ensure_license():
    lic = ROOT / "LICENSE.txt"
    if not lic.exists():
        lic.write_text(textwrap.dedent("""
            PTitu - Organizador de Fotografías
            Universidad Autónoma de Ciudad Juárez
            Ciudad Juárez, Chihuahua, México

            Proyecto de tesis de licenciatura en Ingeniería en Sistemas Computacionales.
            Este software se distribuye únicamente con fines académicos.
            Todos los derechos reservados © 2025 UACJ.
        """).strip())
        print("  ✓ LICENSE.txt creado automáticamente")


def ensure_readme():
    readme = ROOT / "README.txt"
    if not readme.exists():
        readme.write_text(textwrap.dedent("""
            PTitu - Organizador de Fotografías
            Universidad Autónoma de Ciudad Juárez
            =======================================

            INICIO RÁPIDO
            -------------
            1. Ejecuta PTitu.exe
            2. Haz clic en "Importar Fotos" y selecciona una carpeta
            3. Espera el procesamiento automático (aprox. 10-30 seg/foto)
            4. Explora tu colección organizada en la Galería

            CATEGORÍAS DE ESCENAS
            ---------------------
            • Interiores              • Restaurantes
            • Exteriores              • Eventos Sociales
            • Actividades Deportivas

            MODO DESARROLLO (requiere Python 3.10+)
            ----------------------------------------
            Ejecuta install_deps.bat para instalar las dependencias Python.
            Luego: python src/main.py
        """).strip())
        print("  ✓ README.txt creado automáticamente")


# ── Verificación de prerrequisitos ────────────────────────────────────────────

def check_prerequisites() -> bool:
    print("\n─── Verificando prerrequisitos ───")
    ok = True

    # Python
    if sys.version_info < (3, 10):
        print(f"  ✗ Python 3.10+ requerido  (tienes {sys.version.split()[0]})")
        ok = False
    else:
        print(f"  ✓ Python {sys.version.split()[0]}")

    # Modelo VGG-16
    model = ROOT / "data/models/vgg16_scene_classifier.pth"
    if model.exists() and model.stat().st_size >= VGG_MIN_SIZE:
        print(f"  ✓ Modelo VGG-16  ({model.stat().st_size / 1e6:.0f} MB)")
    elif model.exists():
        size_mb = model.stat().st_size / 1e6
        print(f"  ⚠ Modelo VGG-16 parece incompleto ({size_mb:.2f} MB — esperado ≥10 MB)")
        print(f"    ¿Olvidaste ejecutar  git lfs pull  ?")
        ok = False
    else:
        print(f"  ✗ Modelo VGG-16 no encontrado: {model}")
        print(f"    Entrena con:  python scripts/train_scene_classifier.py")
        ok = False

    # Archivos esenciales del proyecto
    essential = {
        "PTitu_installer.iss": "Script de Inno Setup — debe estar en la raíz",
        "runtime_hook.py":     "Hook de arranque para el ejecutable",
        "requirements.txt":    "Lista de dependencias Python",
    }
    for fname, desc in essential.items():
        path = ROOT / fname
        if path.exists():
            print(f"  ✓ {fname}")
        else:
            print(f"  ✗ Falta {fname}  —  {desc}")
            ok = False

    # Archivos que se crean automáticamente si faltan
    for fname in ("LICENSE.txt", "README.txt"):
        path = ROOT / fname
        status = "✓" if path.exists() else "⚠ (se creará automáticamente)"
        print(f"  {status} {fname}")

    # Iconos SVG
    icons_dir = ROOT / "src/ui/icons"
    svgs = list(icons_dir.glob("*.svg")) if icons_dir.exists() else []
    if svgs:
        print(f"  ✓ Iconos SVG ({len(svgs)} archivos)")
    else:
        print(f"  ⚠ Sin iconos — ejecuta:  python setup_icons.py")

    # PyInstaller
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print(f"  ⚠ PyInstaller no instalado  (se instalará automáticamente)")

    # Inno Setup
    iscc = find_iscc()
    if iscc:
        print(f"  ✓ Inno Setup: {iscc}")
    else:
        print(f"  ⚠ Inno Setup no encontrado")
        print(f"    Descarga gratuita: https://jrsoftware.org/isinfo.php")
        print(f"    Sin él solo se genera el .exe, no el instalador.")

    print()
    return ok


# ── Paso 1: compilar con PyInstaller ─────────────────────────────────────────

def step_pyinstaller():
    print("\n─── Compilando con PyInstaller ───")

    if not check_prerequisites():
        print("✗ Corrige los errores anteriores antes de compilar.")
        sys.exit(1)

    ensure_license()
    ensure_readme()

    # Descargar iconos si faltan
    icons_dir = ROOT / "src/ui/icons"
    if not icons_dir.exists() or not list(icons_dir.glob("*.svg")):
        print("  Descargando iconos...")
        run([sys.executable, "setup_icons.py"])

    # Instalar PyInstaller si falta
    try:
        import PyInstaller
    except ImportError:
        print("  Instalando PyInstaller...")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Limpiar builds anteriores
    for folder in ["build", "dist"]:
        p = ROOT / folder
        if p.exists():
            shutil.rmtree(p)
            print(f"  ✓ Limpiado: {folder}/")

    # Compilar
    print("\n  Ejecutando PyInstaller (puede tardar 5-15 min)...")
    run([sys.executable, "-m", "PyInstaller", "PTitu.spec", "--clean", "--noconfirm"])

    # Verificar resultado
    exe = ROOT / "dist/organizador/organizador.exe"
    if not exe.exists():
        print("✗ No se generó dist/organizador/organizador.exe")
        sys.exit(1)

    # Copiar modelo VGG-16 si PyInstaller no lo incluyó
    model_dest = ROOT / "dist/organizador/data/models"
    model_dest.mkdir(parents=True, exist_ok=True)
    model_src = ROOT / "data/models/vgg16_scene_classifier.pth"
    if model_src.exists() and not (model_dest / model_src.name).exists():
        shutil.copy2(model_src, model_dest)
        print("  ✓ Modelo VGG-16 copiado a dist/PTitu/data/models/")

    size_mb = sum(
        f.stat().st_size for f in (ROOT / "dist/PTitu").rglob("*") if f.is_file()
    ) / 1e6
    print(f"\n  ✓ dist/PTitu/PTitu.exe listo  ({size_mb:.0f} MB en total)")


# ── Paso 2: generar instalador con Inno Setup ─────────────────────────────────

def step_inno():
    print("\n─── Generando instalador con Inno Setup ───")

    # Verificar dist/PTitu/
    if not (ROOT / "dist/PTitu").exists():
        print("  ✗ dist/PTitu/ no existe.")
        print("    Ejecuta primero:  python build.py --only-exe")
        sys.exit(1)

    iscc = find_iscc()
    if iscc is None:
        print("\n  ⚠ Inno Setup no encontrado — instalador no generado.")
        print("  Descárgalo (gratis, open source) desde:")
        print("    https://jrsoftware.org/isinfo.php")
        print()
        print("  Una vez instalado vuelve a ejecutar:")
        print("    python build.py --only-installer")
        print()
        print("  El ejecutable ya está disponible en:  dist/PTitu/PTitu.exe")
        return

    iss = ROOT / "PTitu_installer.iss"
    if not iss.exists():
        print(f"  ✗ {iss.name} no encontrado en la raíz del proyecto.")
        sys.exit(1)

    ensure_license()
    ensure_readme()

    # Asegurarse de que install_deps.bat existe
    bat = ROOT / "install_deps.bat"
    if not bat.exists():
        print("  ⚠ install_deps.bat no encontrado — el instalador lo omitirá")

    # Compilar el instalador
    print(f"  Compilador: {iscc}")
    print(f"  Script:     {iss.name}")
    print()
    run([str(iscc), str(iss)])

    # Buscar el .exe generado en Output/
    output_dir = ROOT / "Output"
    installers = sorted(output_dir.glob("PTitu_Setup*.exe")) if output_dir.exists() else []

    if installers:
        installer = installers[-1]   # el más reciente
        size_mb = installer.stat().st_size / 1e6
        print(f"\n  ✓ Instalador generado: {installer.name}  ({size_mb:.0f} MB)")
        print(f"    Ruta completa: {installer}")
    else:
        print("\n  ✗ No se encontró el instalador en Output/")
        print("    Revisa los mensajes de error de Inno Setup arriba.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compilador e instalador de PTitu (usa Inno Setup)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Ejemplos:
              python build.py                   Proceso completo (PyInstaller + Inno Setup)
              python build.py --only-exe        Solo compilar ejecutable
              python build.py --only-installer  Solo generar instalador
              python build.py --check           Verificar prerrequisitos
        """)
    )
    parser.add_argument("--only-exe",        action="store_true",
                        help="Solo compilar con PyInstaller")
    parser.add_argument("--only-installer",  action="store_true",
                        help="Solo generar instalador con Inno Setup")
    parser.add_argument("--check",           action="store_true",
                        help="Solo verificar prerrequisitos")
    args = parser.parse_args()

    print("=" * 60)
    print("   PTitu — Compilador e Instalador")
    print("   Universidad Autónoma de Ciudad Juárez")
    print("=" * 60)

    if args.check:
        ok = check_prerequisites()
        sys.exit(0 if ok else 1)
    elif args.only_installer:
        step_inno()
    elif args.only_exe:
        step_pyinstaller()
    else:
        step_pyinstaller()
        step_inno()

    # Resumen final
    print("\n" + "=" * 60)
    print("   ✓ PROCESO COMPLETADO")
    print("=" * 60)

    output_dir = ROOT / "Output"
    installers = sorted(output_dir.glob("PTitu_Setup*.exe")) if output_dir.exists() else []
    if installers:
        sz = installers[-1].stat().st_size / 1e6
        print(f"\n  Instalador: {installers[-1].name}  ({sz:.0f} MB)  ← distribuye este")
    if (ROOT / "dist/organizador/organizador.exe").exists():
        print(f"  Ejecutable: dist/organizador/organizador.exe  ← para pruebas directas")
    print()


if __name__ == "__main__":
    main()