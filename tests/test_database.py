"""
Pruebas básicas del gestor de base de datos
"""
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import DatabaseManager
from datetime import datetime


def test_database():
    """Prueba básica de operaciones de base de datos"""
    
    print("="*60)
    print("   PRUEBA DEL GESTOR DE BASE DE DATOS")
    print("="*60 + "\n")
    
    # Crear instancia
    db = DatabaseManager()
    
    try:
        # 1. Insertar una fotografía de prueba
        print("1. Insertando fotografía de prueba...")
        photo_data = {
            'file_path': '/ruta/test/foto1.jpg',
            'file_name': 'foto1.jpg',
            'file_size': 1024000,
            'width': 1920,
            'height': 1080,
            'format': '.jpg',
            'timestamp': datetime.now()
        }
        photo_id = db.insert_photo(photo_data)
        print(f"   ✓ Fotografía insertada con ID: {photo_id}\n")
        
        # 2. Insertar metadatos
        print("2. Insertando metadatos...")
        metadata = {
            'camera_make': 'Canon',
            'camera_model': 'EOS 5D Mark IV',
            'iso': 800,
            'aperture': 2.8,
            'gps_latitude': 31.7333,
            'gps_longitude': -106.4833
        }
        db.insert_metadata(photo_id, metadata)
        print("   ✓ Metadatos insertados\n")
        
        # 3. Obtener la fotografía
        print("3. Recuperando fotografía...")
        photo = db.get_photo_by_id(photo_id)
        print(f"   ✓ Fotografía recuperada: {photo['file_name']}\n")
        
        # 4. Obtener metadatos
        print("4. Recuperando metadatos...")
        meta = db.get_metadata(photo_id)
        print(f"   ✓ Cámara: {meta['camera_make']} {meta['camera_model']}")
        print(f"   ✓ GPS: {meta['gps_latitude']}, {meta['gps_longitude']}\n")
        
        # 5. Crear una persona
        print("5. Creando persona...")
        person_id = db.insert_person(cluster_id=1, name="Persona de Prueba")
        print(f"   ✓ Persona creada con ID: {person_id}\n")
        
        # 6. Insertar etiqueta
        print("6. Añadiendo etiqueta...")
        db.insert_tag(photo_id, "vacaciones")
        tags = db.get_tags(photo_id)
        print(f"   ✓ Etiquetas: {tags}\n")
        
        # 7. Obtener estadísticas
        print("7. Estadísticas de la base de datos:")
        stats = db.get_statistics()
        for key, value in stats.items():
            print(f"   • {key}: {value}")
        
        print("\n" + "="*60)
        print("✓ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()
    
    return True


if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)