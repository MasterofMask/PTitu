"""
clean_persons.py — Limpieza quirúrgica de registros de personas problemáticos.

Elimina:
  • Personas sin nombre (generadas por clustering automático)
  • Personas con cluster_id almacenado como bytes (datos corruptos)
  • Personas sin fotos asociadas (registros huérfanos)

Conserva INTACTAS:
  • Todas las personas con nombre asignado manualmente

Uso:
    python clean_persons.py
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


def safe_cluster_id(cid) -> int:
    """Convierte cluster_id a int de forma segura sin importar el tipo."""
    if isinstance(cid, (bytes, bytearray)):
        return int.from_bytes(cid[:4], 'little') if cid else 0
    try:
        return int(cid)
    except (TypeError, ValueError):
        return 0


def main():
    print("=" * 60)
    print("   LIMPIEZA DE PERSONAS PROBLEMÁTICAS")
    print("=" * 60)

    db_path = get_db_path()
    print(f"\nBase de datos: {db_path.resolve()}\n")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # ── Estado inicial ────────────────────────────────────────────────
    rows = conn.execute("""
        SELECT p.id, p.name, p.cluster_id,
               COUNT(DISTINCT f.photo_id) as foto_count
        FROM persons p
        LEFT JOIN faces f ON p.id = f.person_id
        GROUP BY p.id
        ORDER BY p.name NULLS LAST
    """).fetchall()

    print(f"{'ID':>4}  {'Nombre':<25}  {'cluster_id':>15}  {'Fotos':>5}  Estado")
    print("─" * 70)

    to_delete_ids = []      # IDs a eliminar
    to_fix = []             # (id, new_cluster_id) a reparar cluster_id bytes

    for row in rows:
        pid       = row['id']
        name      = row['name']
        cid_raw   = row['cluster_id']
        foto_count = row['foto_count']

        cid_safe = safe_cluster_id(cid_raw)
        cid_bytes = isinstance(cid_raw, (bytes, bytearray))

        # Decidir estado
        is_desconocido = name and (
            name == 'Desconocido' or
            (name.startswith('Desconocido ') and name[12:].strip().isdigit())
        )

        if not name:
            # Sin nombre → candidato a eliminar
            status = "❌ SIN NOMBRE (se eliminará)"
            to_delete_ids.append(pid)
        elif is_desconocido and foto_count == 0:
            # Desconocido sin fotos → huérfano de corrida anterior
            status = "❌ DESCONOCIDO SIN FOTOS (se eliminará)"
            to_delete_ids.append(pid)
        elif cid_bytes:
            # Tiene nombre pero cluster_id corrupto → reparar cluster_id
            status = f"⚠  cluster_id bytes → se corrige a {cid_safe}"
            to_fix.append((pid, cid_safe))
        else:
            status = "✓  OK"

        cid_display = repr(cid_raw) if cid_bytes else str(cid_raw)
        print(f"{pid:>4}  {str(name or '—'):<25}  {cid_display:>15}  {foto_count:>5}  {status}")

    print()

    if not to_delete_ids and not to_fix:
        print("✓ No hay nada que limpiar. La base de datos está limpia.")
        conn.close()
        return

    # ── Confirmación ──────────────────────────────────────────────────
    print(f"Se eliminarán  : {len(to_delete_ids)} persona(s) sin nombre")
    print(f"Se repararán   : {len(to_fix)} cluster_id(s) corruptos")
    print()
    confirm = input("¿Continuar? (escribe 'SI' para confirmar): ").strip()
    if confirm != "SI":
        print("Operación cancelada.")
        conn.close()
        return

    # ── Eliminar personas sin nombre ──────────────────────────────────
    deleted = 0
    for pid in to_delete_ids:
        # Desasignar sus rostros (no borrar los rostros, solo quitarles la persona)
        conn.execute("UPDATE faces SET person_id = NULL WHERE person_id = ?", (pid,))
        conn.execute("DELETE FROM persons WHERE id = ?", (pid,))
        deleted += 1

    # ── Reparar cluster_id bytes ──────────────────────────────────────
    fixed = 0
    for pid, new_cid in to_fix:
        # Verificar que el nuevo cluster_id no colisione
        while conn.execute(
            "SELECT 1 FROM persons WHERE cluster_id = ? AND id != ?",
            (new_cid, pid)
        ).fetchone():
            new_cid += 1
        conn.execute("UPDATE persons SET cluster_id = ? WHERE id = ?", (new_cid, pid))
        fixed += 1

    conn.commit()

    # ── Estado final ──────────────────────────────────────────────────
    print(f"\n✓ {deleted} persona(s) eliminada(s)")
    print(f"✓ {fixed} cluster_id(s) reparado(s)")

    print("\nEstado final de personas:")
    print("─" * 45)
    final_rows = conn.execute("""
        SELECT p.name, p.cluster_id, COUNT(DISTINCT f.photo_id) as fotos
        FROM persons p
        LEFT JOIN faces f ON p.id = f.person_id
        GROUP BY p.id
        ORDER BY fotos DESC
    """).fetchall()

    for r in final_rows:
        print(f"  • {r['name'] or '—':<25}  cluster={r['cluster_id']}  {r['fotos']} foto(s)")

    conn.close()
    print("\n✓ LIMPIEZA COMPLETADA")


if __name__ == "__main__":
    main()