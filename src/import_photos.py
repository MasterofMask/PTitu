"""
Script para importar y procesar una colección de fotografías
"""
import sys
from pathlib import Path
from tqdm import tqdm

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import DatabaseManager
from src.core.config import SUPPORTED_FORMATS
from src.processors.metadata_processor import MetadataProcessor
from src.processors.face_processor import FaceProcessor
from src.clustering.face_clustering import FaceClustering
from src.models.photo import Photo


def import_and_process_folder(folder_path: Path, 
                               process_faces: bool = True,
                               cluster_faces: bool = True):
    """
    Importa y procesa todas las fotos de una carpeta.
    
    Args:
        folder_path: Ruta a la carpeta con fotos
        process_faces: Si True, detecta rostros
        cluster_faces: Si True, agrupa rostros por persona
    """
    # Inicializar componentes
    db = DatabaseManager()
    metadata_processor = MetadataProcessor()
    
    face_processor = None
    if process_faces:
        print("Inicializando detector de rostros...")
        face_processor = FaceProcessor()
        print("✓ Detector inicializado\n")
    
    # Buscar archivos de imagen
    image_files = []
    for ext in SUPPORTED_FORMATS:
        image_files.extend(folder_path.rglob(f"*{ext}"))
        image_files.extend(folder_path.rglob(f"*{ext.upper()}"))
    
    print(f"Encontradas {len(image_files)} imágenes en {folder_path}")
    
    if not image_files:
        print("No se encontraron imágenes para importar.")
        return
    
    imported = 0
    errors = 0
    total_faces = 0
    
    # Procesar cada imagen
    print("\nImportando y procesando imágenes...")
    for image_file in tqdm(image_files, desc="Procesando"):
        try:
            # Crear objeto Photo
            photo = Photo.from_file(image_file)
            
            # Extraer metadatos
            metadata = metadata_processor.process_file(image_file)
            
            # Actualizar timestamp si está en metadatos
            if metadata.get('timestamp'):
                photo.timestamp = metadata['timestamp']
            
            # Insertar en base de datos
            photo_id = db.insert_photo(photo.to_dict())
            
            # Insertar metadatos si existen
            if metadata:
                db.insert_metadata(photo_id, metadata)
            
            # Procesar rostros si está habilitado
            if process_faces and face_processor:
                faces = face_processor.process_image(image_file)
                
                for face in faces:
                    face['photo_id'] = photo_id
                    db.insert_face(face)
                    total_faces += 1
            
            # Marcar como procesada
            db.update_photo_processed(photo_id)
            
            imported += 1
            
        except Exception as e:
            errors += 1
            tqdm.write(f"Error con {image_file.name}: {e}")
    
    print(f"\n✓ Importadas: {imported}")
    print(f"✓ Rostros detectados: {total_faces}")
    if errors > 0:
        print(f"✗ Errores: {errors}")
    
    # Ejecutar clustering si está habilitado
    if cluster_faces and total_faces > 0:
        print("\nEjecutando clustering facial...")
        clusterer = FaceClustering()
        clusters = clusterer.cluster_from_database(db)
        
        stats = clusterer.get_cluster_statistics()
        print(f"✓ Identificadas {stats['n_clusters']} persona(s)")
    
    # Mostrar estadísticas finales
    print("\n" + "="*60)
    print("Estadísticas finales:")
    stats = db.get_statistics()
    print(f"  Total de fotos: {stats['total_photos']}")
    print(f"  Fotos procesadas: {stats['processed_photos']}")
    print(f"  Rostros detectados: {stats['total_faces']}")
    print(f"  Personas identificadas: {stats['total_persons']}")
    print(f"  Fotos con GPS: {stats['photos_with_gps']}")
    print("="*60)
    
    db.close()


def main():
    """Función principal"""
    print("="*60)
    print("   IMPORTADOR DE COLECCIONES FOTOGRÁFICAS")
    print("="*60 + "\n")
    
    # Solicitar carpeta
    print("Ingresa la ruta de la carpeta con fotografías:")
    print("(Ejemplo: C:/Users/tu_usuario/Pictures/Vacaciones)")
    folder_input = input("\nRuta: ").strip().strip('"')
    
    if not folder_input:
        print("No se proporcionó ruta. Importación cancelada.")
        return
    
    folder_path = Path(folder_input)
    
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"✗ Carpeta no válida: {folder_path}")
        return
    
    # Opciones de procesamiento
    print("\n¿Detectar rostros? (s/n): ", end="")
    process_faces = input().strip().lower() == 's'
    
    cluster_faces = False
    if process_faces:
        print("¿Agrupar rostros por persona? (s/n): ", end="")
        cluster_faces = input().strip().lower() == 's'
    
    try:
        # Importar y procesar
        import_and_process_folder(folder_path, process_faces, cluster_faces)
        
        print("\n✓ IMPORTACIÓN COMPLETADA")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()