"""
Script para limpiar la base de datos de duplicados
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import DatabaseManager


def clean_database():
    """Limpia duplicados de la base de datos"""
    print("="*60)
    print("   LIMPIEZA DE BASE DE DATOS")
    print("="*60 + "\n")
    
    db = DatabaseManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    # 1. Encontrar y eliminar fotos duplicadas
    print("Buscando fotos duplicadas...")
    
    cursor.execute("""
        SELECT file_path, COUNT(*) as count, GROUP_CONCAT(id) as ids
        FROM photos
        GROUP BY file_path
        HAVING count > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"Encontradas {len(duplicates)} rutas duplicadas\n")
        
        for dup in duplicates:
            file_path = dup['file_path']
            ids = dup['ids'].split(',')
            
            # Mantener el primero, eliminar los demás
            keep_id = ids[0]
            delete_ids = ids[1:]
            
            print(f"Ruta: {file_path}")
            print(f"  Manteniendo ID: {keep_id}")
            print(f"  Eliminando IDs: {', '.join(delete_ids)}")
            
            for del_id in delete_ids:
                cursor.execute("DELETE FROM photos WHERE id = ?", (del_id,))
            
            print()
        
        conn.commit()
        print(f"✓ Eliminados {sum(len(d['ids'].split(','))-1 for d in duplicates)} registros duplicados\n")
    else:
        print("✓ No se encontraron duplicados\n")
    
    # 2. Eliminar registros huérfanos
    print("Limpiando registros huérfanos...")
    
    # Metadatos sin foto
    cursor.execute("""
        DELETE FROM metadata 
        WHERE photo_id NOT IN (SELECT id FROM photos)
    """)
    orphan_metadata = cursor.rowcount
    
    # Rostros sin foto
    cursor.execute("""
        DELETE FROM faces 
        WHERE photo_id NOT IN (SELECT id FROM photos)
    """)
    orphan_faces = cursor.rowcount
    
    # Escenas sin foto
    cursor.execute("""
        DELETE FROM scenes 
        WHERE photo_id NOT IN (SELECT id FROM photos)
    """)
    orphan_scenes = cursor.rowcount
    
    # Etiquetas sin foto
    cursor.execute("""
        DELETE FROM tags 
        WHERE photo_id NOT IN (SELECT id FROM photos)
    """)
    orphan_tags = cursor.rowcount
    
    conn.commit()
    
    print(f"  Metadatos huérfanos: {orphan_metadata}")
    print(f"  Rostros huérfanos: {orphan_faces}")
    print(f"  Escenas huérfanas: {orphan_scenes}")
    print(f"  Etiquetas huérfanas: {orphan_tags}\n")
    
    # 3. Estadísticas finales
    print("Estadísticas actualizadas:")
    stats = db.get_statistics()
    
    print(f"  Fotos: {stats['total_photos']}")
    print(f"  Rostros: {stats['total_faces']}")
    print(f"  Personas: {stats['total_persons']}")
    print(f"  Fotos con GPS: {stats['photos_with_gps']}")
    
    print("\n" + "="*60)
    print("✓ LIMPIEZA COMPLETADA")
    print("="*60)
    
    db.close()


if __name__ == "__main__":
    clean_database()