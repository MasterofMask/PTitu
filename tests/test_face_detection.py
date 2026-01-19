"""
Pruebas del detector de rostros
"""
import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.face_processor import FaceProcessor
from src.core.database import DatabaseManager


def test_face_detection():
    """Prueba la detección de rostros en una imagen"""
    
    print("="*60)
    print("   PRUEBA DEL DETECTOR DE ROSTROS")
    print("="*60 + "\n")
    
    # Solicitar imagen
    print("Proporciona la ruta de una imagen con rostros:")
    print("(Ejemplo: C:/Users/tu_usuario/Pictures/foto_personas.jpg)")
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
        # Crear procesador
        print("Inicializando detector de rostros...")
        processor = FaceProcessor()
        print("✓ Detector inicializado\n")
        
        # Procesar imagen
        print("Detectando rostros...")
        faces = processor.process_image(image_path)
        
        if not faces:
            print("⚠ No se detectaron rostros en la imagen")
            return True
        
        # Mostrar resultados
        print(f"\n✓ Detectados {len(faces)} rostro(s):\n")
        print("-" * 60)
        
        for i, face in enumerate(faces, 1):
            print(f"\nRostro {i}:")
            print(f"  • Posición: ({face['bbox_x']}, {face['bbox_y']})")
            print(f"  • Tamaño: {face['bbox_width']}x{face['bbox_height']} px")
            print(f"  • Confianza: {face['confidence']:.2%}")
            print(f"  • Embedding: {face['embedding'].shape}")
        
        print("\n" + "-" * 60)
        
        # Visualizar detecciones
        print("\n¿Generar imagen con rostros marcados? (s/n): ", end="")
        visualize = input().strip().lower()
        
        if visualize == 's':
            output_dir = Path("data/detections")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"detected_{image_path.name}"
            
            processor.visualize_detections(image_path, faces, output_path)
            print(f"✓ Imagen guardada en: {output_path}")
        
        # Guardar en base de datos
        print("\n¿Guardar detecciones en base de datos? (s/n): ", end="")
        save = input().strip().lower()
        
        if save == 's':
            from src.models.photo import Photo
            
            db = DatabaseManager()
            
            # Verificar si la foto ya está en BD
            photo = Photo.from_file(image_path)
            photo_id = db.insert_photo(photo.to_dict())
            
            # Insertar rostros
            for face in faces:
                face['photo_id'] = photo_id
                db.insert_face(face)
            
            print(f"✓ Guardados {len(faces)} rostro(s) en la base de datos")
            
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
    success = test_face_detection()
    sys.exit(0 if success else 1)