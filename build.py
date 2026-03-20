#!/usr/bin/env python3
"""
build.py — Compila PTitu y genera el instalador Windows.

Pasos automáticos:
  1. Verifica prerrequisitos
  2. Compila con PyInstaller → dist/PTitu/
  3. Genera instalador con NSIS → PTitu_Setup.exe

Uso:
    python build.py                   # todo el proceso
    python build.py --only-exe        # solo PyInstaller
    python build.py --only-installer  # solo NSIS
"""
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

ROOT = Path(__file__).parent

NSIS_PATHS = [
    Path("C:/Program Files (x86)/NSIS/makensis.exe"),
    Path("C:/Program Files/NSIS/makensis.exe"),
]


def run(cmd):
    print(f"\n> {' '.join(str(c) for c in cmd)}\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\n✗ Fallo. Revisa los mensajes anteriores.")
        sys.exit(1)


def check_file(path, description):
    if not path.exists():
        print(f"\n✗ No se encontró: {path}\n  {description}")
        sys.exit(1)
    print(f"  ✓ {path.name}")


def find_nsis():
    for p in NSIS_PATHS:
        if p.exists():
            return p
    r = shutil.which("makensis")
    return Path(r) if r else None


def step_pyinstaller():
    print("\n─── Verificando prerrequisitos ───")
    check_file(ROOT / "data/models/vgg16_scene_classifier.pth",
               "Entrena el modelo primero.")
    check_file(ROOT / "PTitu.spec",      "Copia PTitu.spec a la raíz.")
    check_file(ROOT / "runtime_hook.py", "Copia runtime_hook.py a la raíz.")

    icons_dir = ROOT / "src/ui/icons"
    if not icons_dir.exists() or not list(icons_dir.glob("*.svg")):
        print("  Descargando iconos...")
        run([sys.executable, "setup_icons.py"])
    else:
        print(f"  ✓ iconos ({len(list(icons_dir.glob('*.svg')))} SVGs)")

    try:
        import PyInstaller
        print(f"  ✓ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("\n─── Limpiando builds anteriores ───")
    for f in ["build", "dist"]:
        p = ROOT / f
        if p.exists():
            shutil.rmtree(p)
            print(f"  ✓ Eliminado: {f}/")

    print("\n─── Compilando con PyInstaller (5-15 min) ───")
    run([sys.executable, "-m", "PyInstaller", "PTitu.spec", "--clean", "--noconfirm"])

    exe = ROOT / "dist/PTitu/PTitu.exe"
    if not exe.exists():
        print("\n✗ No se generó PTitu.exe"); sys.exit(1)

    size = sum(f.stat().st_size for f in (ROOT / "dist/PTitu").rglob("*") if f.is_file()) / 1e6
    print(f"\n  ✓ dist/PTitu/PTitu.exe ({size:.0f} MB total)")


def step_nsis():
    print("\n─── Generando instalador NSIS ───")

    if not (ROOT / "dist/PTitu").exists():
        print("  ✗ dist/PTitu/ no existe. Ejecuta primero --only-exe"); sys.exit(1)

    makensis = find_nsis()
    if makensis is None:
        print("\n  ⚠ NSIS no encontrado.")
        print("  Descárgalo: https://nsis.sourceforge.io/Download")
        print("  Luego: python build.py --only-installer")
        print("\n  El ejecutable ya está en dist/PTitu/PTitu.exe")
        return

    print(f"  ✓ NSIS: {makensis}")

    nsi = ROOT / "PTitu_installer.nsi"
    check_file(nsi, "Copia PTitu_installer.nsi a la raíz.")

    if not (ROOT / "LICENSE.txt").exists():
        (ROOT / "LICENSE.txt").write_text(
            "PTitu - Organizador de Fotografías\n"
            "Universidad Autónoma de Ciudad Juárez\n\n"
            "Proyecto de tesis de licenciatura.\n"
        )
        print("  ✓ LICENSE.txt creado")

    run([str(makensis), str(nsi)])

    setup = ROOT / "PTitu_Setup.exe"
    if setup.exists():
        size_mb = setup.stat().st_size / 1e6
        print(f"\n  ✓ PTitu_Setup.exe ({size_mb:.0f} MB)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-exe",       action="store_true")
    parser.add_argument("--only-installer", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("   COMPILANDO PTitu para Windows")
    print("=" * 60)

    if args.only_installer:
        step_nsis()
    elif args.only_exe:
        step_pyinstaller()
    else:
        step_pyinstaller()
        step_nsis()

    print("\n" + "=" * 60)
    print("   ✓ PROCESO COMPLETADO")
    print("=" * 60)

    if (ROOT / "PTitu_Setup.exe").exists():
        print("\n  Instalador : PTitu_Setup.exe  ← distribuye este archivo")
    if (ROOT / "dist/PTitu/PTitu.exe").exists():
        print("  Ejecutable : dist/PTitu/PTitu.exe")
    print()


if __name__ == "__main__":
    main()
