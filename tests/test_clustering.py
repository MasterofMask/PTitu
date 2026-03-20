"""
Pruebas del clustering facial
"""
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clustering.face_clustering import FaceClustering
from src.core.database import DatabaseManager


def test_clustering():
    """Prueba el clustering de rostros desde la base de datos"""

    print("=" * 60)
    print("   PRUEBA DE CLUSTERING FACIAL")
    print("=" * 60 + "\n")

    db = DatabaseManager()

    try:
        stats = db.get_statistics()

        if stats['total_faces'] == 0:
            print("⚠ No hay rostros en la base de datos.")
            print("  Ejecuta primero: python tests/test_face_detection.py")
            return False

        print(f"Rostros en base de datos : {stats['total_faces']}")
        print(f"Personas ya identificadas: {stats['total_persons']}\n")

        # Mostrar estado de personas ANTES del clustering
        print("Personas antes del clustering:")
        print("-" * 60)
        for p in db.get_all_persons():
            name = p['name'] or f"[sin nombre] cluster_id={p['cluster_id']}"
            print(f"  ID={p['id']:>3}  {name:<30}  {p['photo_count']} foto(s)")
        print()

        print("Ejecutando clustering...")
        clusterer = FaceClustering()
        clusters = clusterer.cluster_from_database(db)

        stats_cl = clusterer.get_cluster_statistics()

        print("\nResultados del clustering:")
        print("-" * 60)
        print(f"\n  Total de rostros    : {stats_cl.get('n_total', 0)}")
        print(f"  Grupos nuevos DBSCAN: {stats_cl.get('n_clusters', 0)}")
        print(f"  Sin clasificar      : {stats_cl.get('n_noise', 0)}")
        print(f"\n  eps        : {stats_cl.get('parameters', {}).get('eps')}")
        print(f"  min_samples: {stats_cl.get('parameters', {}).get('min_samples')}")

        if stats_cl.get('cluster_sizes'):
            print("\n  Distribución clusters nuevos:")
            for cid, size in stats_cl['cluster_sizes'].items():
                print(f"    Cluster {cid}: {size} rostro(s)")

        # Mostrar estado DESPUÉS
        print("\nPersonas después del clustering:")
        print("-" * 60)
        for p in db.get_all_persons():
            name = p['name'] or f"[sin nombre] cluster_id={p['cluster_id']}"
            print(f"  ID={p['id']:>3}  {name:<30}  {p['photo_count']} foto(s)")

        print("\n" + "=" * 60)
        print("✓ CLUSTERING COMPLETADO")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = test_clustering()
    sys.exit(0 if success else 1)