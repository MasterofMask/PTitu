"""
reset_database.py — Limpia completamente la base de datos.

No requiere ningún método especial del DatabaseManager.

Uso:
    python reset_database.py
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def get_db_path():
    """Obtiene la ruta de la BD desde config, con fallback manual."""
    try:
        from src.core.config import DATABASE_PATH
        return Path(DATABASE_PATH)
    except Exception:
        candidates = [
            Path("data/photos.db"),
            Path("data/database.db"),
            Path("photos.db"),
        ]
        for p in candidates:
            if p.exists():
                return p
        raise FileNotFoundError(
            "No se encontró la base de datos. "
            "Verifica la ruta en src/core/config.py"
        )


def main():
    print("=" * 60)
    print("   RESET COMPLETO DE BASE DE DATOS")
    print("=" * 60)
    print()

    db_path = get_db_path()
    print(f"Base de datos: {db_path.resolve()}")
    print()
    print("⚠  Esto eliminará TODOS los registros (fotos, rostros,")
    print("   escenas, personas y etiquetas).")
    print()
    confirm = input("¿Continuar? (escribe 'SI' para confirmar): ").strip()

    if confirm != "SI":
        print("Operación cancelada.")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")

    tables = ['tags', 'scenes', 'faces', 'persons', 'metadata', 'photos']

    print("\nAntes del reset:")
    for t in tables:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:<12}: {n}")
        except Exception:
            pass

    print("\nVaciando tablas...")
    for t in tables:
        try:
            conn.execute(f"DELETE FROM {t}")
            print(f"  ✓ {t}")
        except Exception as e:
            print(f"  ✗ {t}: {e}")

    try:
        conn.execute("DELETE FROM sqlite_sequence")
    except Exception:
        pass

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()

    print("\n Base de datos vaciada.")


if __name__ == "__main__":
    main()