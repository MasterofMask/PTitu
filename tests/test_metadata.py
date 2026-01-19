"""
Pruebas del procesador de metadatos
"""
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.metadata_processor import MetadataProcessor
from src.core.database import DatabaseManager
from src.models.photo import Photo


def test_metadata_extraction():
    """Prueba la extracción de metadatos de imágenes reales"""
    
    print("="*60)
    print("   PRUEBA DEL PROCESADOR DE METADATOS")
    print("="*60 + "\n")
    
    # Crear procesador
    processor = MetadataProcessor()
    
    # Solicitar ruta de imagen de prueba
    print("Por favor, proporciona la ruta de una imagen JPEG con EXIF:")
    print("(Ejemplo: C:/Users/tu_usuario/Pictures/foto.jpg)")
    image_path = input("\nRuta: ").strip().strip('"')
    
    if not image_path:
        print("No se proporcionó ruta. Prueba cancelada.")
        return False
    
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"✗ Archivo no encontrado: {image_path}")
        return False
    
    print(f"\nProcesando: {image_path.name}\n")
    
    try:
        # Extraer metadatos
        metadata = processor.process_file(image_path)
        
        if not metadata:
            print("⚠ No se encontraron metadatos EXIF")
            return False
        
        # Mostrar metadatos extraídos
        print("Metadatos extraídos:")
        print("-" * 60)
        
        if metadata.get('camera_make'):
            print(f"  📷 Cámara: {metadata['camera_make']} {metadata.get('camera_model', '')}")
        
        if metadata.get('timestamp'):
            print(f"  📅 Fecha: {metadata['timestamp']}")
        
        if metadata.get('iso'):
            print(f"  🎞️  ISO: {metadata['iso']}")
        
        if metadata.get('aperture'):
            print(f"  🔍 Apertura: f/{metadata['aperture']}")
        
        if metadata.get('exposure_time'):
            print(f"  ⏱️  Exposición: {metadata['exposure_time']} s")
        
        if metadata.get('focal_length'):
            print(f"  📏 Focal: {metadata['focal_length']} mm")
        
        if metadata.get('gps_latitude') and metadata.get('gps_longitude'):
            print(f"  🌍 GPS: {metadata['gps_latitude']:.6f}, {metadata['gps_longitude']:.6f}")
        
        print("-" * 60)
        
        # Guardar en base de datos
        print("\n¿Guardar en base de datos? (s/n): ", end="")
        save = input().strip().lower()
        
        if save == 's':
            db = DatabaseManager()
            
            # Crear objeto Photo
            photo = Photo.from_file(image_path)
            photo.timestamp = metadata.get('timestamp')
            
            # Insertar fotografía
            photo_id = db.insert_photo(photo.to_dict())
            print(f"✓ Fotografía guardada con ID: {photo_id}")
            
            # Insertar metadatos
            db.insert_metadata(photo_id, metadata)
            print(f"✓ Metadatos guardados")
            
            db.close()
        
        print("\n" + "="*60)
        print("✓ PRUEBA COMPLETADA EXITOSAMENTE")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_metadata_extraction()
    sys.exit(0 if success else 1)