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
    
    print("="*60)
    print("   PRUEBA DE CLUSTERING FACIAL")
    print("="*60 + "\n")
    
    # Conectar a base de datos
    db = DatabaseManager()
    
    try:
        # Verificar que hay rostros
        stats = db.get_statistics()
        
        if stats['total_faces'] == 0:
            print("⚠ No hay rostros en la base de datos.")
            print("  Ejecuta primero: python tests/test_face_detection.py")
            return False
        
        print(f"Rostros en base de datos: {stats['total_faces']}")
        print(f"Personas ya identificadas: {stats['total_persons']}\n")
        
        # Crear clustering
        print("Ejecutando clustering...")
        clusterer = FaceClustering()
        
        # Ejecutar clustering desde BD
        clusters = clusterer.cluster_from_database(db)
        
        # Mostrar resultados
        print("\nResultados del clustering:")
        print("-" * 60)
        
        stats_clustering = clusterer.get_cluster_statistics()
        
        print(f"\n📊 Estadísticas:")
        print(f"  • Total de rostros: {stats_clustering['n_total']}")
        print(f"  • Personas identificadas: {stats_clustering['n_clusters']}")
        print(f"  • Rostros sin clasificar: {stats_clustering['n_noise']}")
        print(f"\n⚙️  Parámetros:")
        print(f"  • eps: {stats_clustering['parameters']['eps']}")
        print(f"  • min_samples: {stats_clustering['parameters']['min_samples']}")
        
        print(f"\n👥 Distribución por persona:")
        for cluster_id, size in stats_clustering['cluster_sizes'].items():
            print(f"  • Persona {cluster_id}: {size} foto(s)")
        
        # Mostrar personas en BD
        print("\n" + "-" * 60)
        print("Personas en la base de datos:")
        persons = db.get_all_persons()
        
        for person in persons:
            name = person['name'] or f"Persona {person['cluster_id']}"
            print(f"  • {name}: {person['photo_count']} foto(s)")
        
        print("\n" + "="*60)
        print("✓ CLUSTERING COMPLETADO EXITOSAMENTE")
        print("="*60)
        
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