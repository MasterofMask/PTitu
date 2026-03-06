"""
fix_cluster_ids.py — Repara cluster_id guardados como bytes en la BD.

Ejecutar UNA VEZ antes de reiniciar la aplicación.

Uso:
    python fix_cluster_ids.py
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def get_db_path():
    try:
        from src.core.config import DATABASE_PATH
        return Path(DATABASE_PATH)
    except Exception:
        for p in [Path("data/photos.db"), Path("data/database.db"), Path("photos.db")]:
            if p.exists():
                return p
        raise FileNotFoundError("No se encontró la base de datos.")


def main():
    print("=" * 60)
    print("   REPARACIÓN DE cluster_id CORRUPTOS")
    print("=" * 60)

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT id, cluster_id, name FROM persons").fetchall()
    fixed = 0

    for row in rows:
        cid = row['cluster_id']
        # Detectar si es bytes o string que no es número
        needs_fix = False
        if isinstance(cid, (bytes, bytearray)):
            needs_fix = True
            new_id = int.from_bytes(cid[:4], 'little') if cid else row['id'] + 9000
        elif isinstance(cid, str):
            needs_fix = True
            # Intentar convertir, si no usar id+9000
            try:
                new_id = int(cid)
            except ValueError:
                new_id = row['id'] + 9000
        else:
            # Ya es int, verificar que no sea negativo ni 0
            new_id = int(cid) if cid and int(cid) > 0 else row['id'] + 9000
            if new_id != cid:
                needs_fix = True

        if needs_fix:
            # Asegurarse de que el nuevo cluster_id no colisione
            while conn.execute(
                "SELECT 1 FROM persons WHERE cluster_id = ? AND id != ?",
                (new_id, row['id'])
            ).fetchone():
                new_id += 1

            conn.execute(
                "UPDATE persons SET cluster_id = ? WHERE id = ?",
                (new_id, row['id'])
            )
            print(f"  Persona '{row['name'] or row['id']}': "
                  f"cluster_id {repr(cid)} → {new_id}")
            fixed += 1

    conn.commit()

    print(f"\n✓ {fixed} registro(s) reparado(s).")

    # Mostrar estado final
    print("\nEstado actual de persons:")
    for row in conn.execute("SELECT id, cluster_id, name FROM persons").fetchall():
        print(f"  id={row['id']}  cluster_id={row['cluster_id']}  name={row['name']}")

    conn.close()


if __name__ == "__main__":
    main()