"""
Prueba del clasificador de escenas
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processors.scene_processor import SceneProcessor


def test_scene_classification():
    """Prueba la clasificación de escenas"""
    
    print("="*60)
    print("   PRUEBA DE CLASIFICACIÓN DE ESCENAS")
    print("="*60 + "\n")
    
    # Solicitar imagen
    print("Proporciona la ruta de una imagen:")
    image_path = input("\nRuta: ").strip().strip('"')
    
    if not image_path:
        print("No se proporcionó ruta.")
        return False
    
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"✗ Archivo no encontrado: {image_path}")
        return False
    
    try:
        # Crear procesador
        print("\nInicializando clasificador...")
        processor = SceneProcessor()
        print("✓ Clasificador inicializado\n")
        
        # Clasificar
        print(f"Clasificando: {image_path.name}\n")
        result = processor.process_image(image_path)
        
        # Mostrar resultado
        print("Resultado:")
        print("-" * 60)
        print(f"  📍 Categoría: {result['category']}")
        print(f"  📊 Confianza: {result['confidence']:.2%}")
        print("-" * 60)
        
        print("\n" + "="*60)
        print("✓ PRUEBA COMPLETADA")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_scene_classification()
    sys.exit(0 if success else 1)