"""
Gestor de base de datos SQLite para la aplicación de organización fotográfica.

Este módulo proporciona la interfaz para interactuar con la base de datos,
incluyendo operaciones CRUD para fotografías, metadatos, personas y etiquetas.
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pickle

from src.core.config import DATABASE_PATH

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Gestor de base de datos SQLite.
    
    Proporciona métodos para crear, leer, actualizar y eliminar registros
    de fotografías, metadatos EXIF, personas detectadas y clasificaciones.
    """
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        """
        Inicializa el gestor de base de datos.
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_database()
    
    def _ensure_database(self):
        """Asegura que la base de datos y tablas existan"""
        self.connect()
        self._create_tables()
        self.close()
    
    def connect(self) -> sqlite3.Connection:
        """
        Establece conexión con la base de datos.
        
        Returns:
            Objeto de conexión SQLite
        """
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row
            # Habilitar claves foráneas
            self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Conexión establecida con {self.db_path}")
        return self.connection
    
    def close(self):
        """Cierra la conexión con la base de datos"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Conexión cerrada")
    
    def _create_tables(self):
        """Crea las tablas necesarias si no existen"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Tabla de fotografías
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                width INTEGER,
                height INTEGER,
                format TEXT,
                timestamp DATETIME,
                date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        """)
        
        # Tabla de metadatos EXIF
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                camera_make TEXT,
                camera_model TEXT,
                focal_length REAL,
                aperture REAL,
                exposure_time TEXT,
                iso INTEGER,
                flash INTEGER,
                gps_latitude REAL,
                gps_longitude REAL,
                gps_altitude REAL,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
            )
        """)
        
        # Tabla de personas detectadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                cluster_id INTEGER NOT NULL,
                date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cluster_id)
            )
        """)
        
        # Tabla de rostros detectados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                person_id INTEGER,
                embedding BLOB NOT NULL,
                bbox_x INTEGER,
                bbox_y INTEGER,
                bbox_width INTEGER,
                bbox_height INTEGER,
                confidence REAL,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL
            )
        """)
        
        # Tabla de escenas clasificadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                confidence REAL NOT NULL,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
            )
        """)
        
        # Tabla de etiquetas personalizadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE,
                UNIQUE(photo_id, tag_name)
            )
        """)
        
        # Índices para optimizar búsquedas
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_photos_timestamp 
            ON photos(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_photos_processed 
            ON photos(processed)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_gps 
            ON metadata(gps_latitude, gps_longitude)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_faces_person 
            ON faces(person_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_faces_photo 
            ON faces(photo_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenes_category 
            ON scenes(category)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_name 
            ON tags(tag_name)
        """)
        
        conn.commit()
        logger.info("Tablas e índices de base de datos creados/verificados")
    
    # ==================== OPERACIONES CON FOTOGRAFÍAS ====================
    
    def insert_photo(self, photo_data: Dict[str, Any]) -> int:
        """
        Inserta una nueva fotografía en la base de datos.
        
        Args:
            photo_data: Diccionario con datos de la fotografía
            
        Returns:
            ID de la fotografía insertada
            
        Raises:
            sqlite3.IntegrityError: Si la foto ya existe
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO photos (
                    file_path, file_name, file_size, width, height, 
                    format, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                photo_data['file_path'],
                photo_data['file_name'],
                photo_data.get('file_size'),
                photo_data.get('width'),
                photo_data.get('height'),
                photo_data.get('format'),
                photo_data.get('timestamp')
            ))
            
            conn.commit()
            photo_id = cursor.lastrowid
            logger.info(f"Fotografía insertada con ID: {photo_id}")
            return photo_id
            
        except sqlite3.IntegrityError as e:
            logger.warning(f"Fotografía ya existe: {photo_data['file_path']}")
            # Obtener ID de la foto existente
            cursor.execute(
                "SELECT id FROM photos WHERE file_path = ?", 
                (photo_data['file_path'],)
            )
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def get_photo_by_id(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene una fotografía por su ID.
        
        Args:
            photo_id: ID de la fotografía
            
        Returns:
            Diccionario con datos de la fotografía o None
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM photos WHERE id = ?", (photo_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_photos(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene todas las fotografías.
        
        Args:
            limit: Número máximo de fotos a retornar
            
        Returns:
            Lista de diccionarios con datos de fotografías
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM photos ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_unprocessed_photos(self) -> List[Dict[str, Any]]:
        """
        Obtiene fotografías no procesadas.
        
        Returns:
            Lista de fotografías pendientes de procesamiento
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM photos 
            WHERE processed = 0 
            ORDER BY date_added ASC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_photo_processed(self, photo_id: int):
        """
        Marca una fotografía como procesada.
        
        Args:
            photo_id: ID de la fotografía
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE photos SET processed = 1 WHERE id = ?",
            (photo_id,)
        )
        conn.commit()
        logger.debug(f"Fotografía ID {photo_id} marcada como procesada")
    
    def delete_photo(self, photo_id: int):
        """
        Elimina una fotografía y todos sus datos relacionados.
        
        Args:
            photo_id: ID de la fotografía
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        logger.info(f"Fotografía ID {photo_id} eliminada")
    
    # ==================== OPERACIONES CON METADATOS ====================
    
    def insert_metadata(self, photo_id: int, metadata: Dict[str, Any]):
        """
        Inserta metadatos EXIF de una fotografía.
        
        Args:
            photo_id: ID de la fotografía
            metadata: Diccionario con metadatos EXIF
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (
                photo_id, camera_make, camera_model, focal_length,
                aperture, exposure_time, iso, flash,
                gps_latitude, gps_longitude, gps_altitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            photo_id,
            metadata.get('camera_make'),
            metadata.get('camera_model'),
            metadata.get('focal_length'),
            metadata.get('aperture'),
            metadata.get('exposure_time'),
            metadata.get('iso'),
            metadata.get('flash'),
            metadata.get('gps_latitude'),
            metadata.get('gps_longitude'),
            metadata.get('gps_altitude')
        ))
        
        conn.commit()
        logger.debug(f"Metadatos insertados para foto ID: {photo_id}")
    
    def get_metadata(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene metadatos de una fotografía.
        
        Args:
            photo_id: ID de la fotografía
            
        Returns:
            Diccionario con metadatos o None
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM metadata WHERE photo_id = ?",
            (photo_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ==================== OPERACIONES CON PERSONAS ====================
    
    def insert_person(self, cluster_id: int, name: Optional[str] = None) -> int:
        """
        Inserta una nueva persona identificada.
        
        Args:
            cluster_id: ID del cluster facial
            name: Nombre opcional de la persona
            
        Returns:
            ID de la persona insertada
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO persons (cluster_id, name)
                VALUES (?, ?)
            """, (cluster_id, name))
            
            conn.commit()
            person_id = cursor.lastrowid
            logger.info(f"Persona insertada con ID: {person_id}, Cluster: {cluster_id}")
            return person_id
            
        except sqlite3.IntegrityError:
            # Persona ya existe, obtener ID
            cursor.execute(
                "SELECT id FROM persons WHERE cluster_id = ?",
                (cluster_id,)
            )
            result = cursor.fetchone()
            return result['id'] if result else None
    
    def get_person_by_id(self, person_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una persona por ID"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM persons WHERE id = ?", (person_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_persons(self) -> List[Dict[str, Any]]:
        """Obtiene todas las personas identificadas"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.*, COUNT(f.id) as photo_count
            FROM persons p
            LEFT JOIN faces f ON p.id = f.person_id
            GROUP BY p.id
            ORDER BY photo_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_person_name(self, person_id: int, name: str):
        """Actualiza el nombre de una persona"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE persons SET name = ? WHERE id = ?",
            (name, person_id)
        )
        conn.commit()
        logger.info(f"Persona ID {person_id} renombrada a '{name}'")
    
    # ==================== OPERACIONES CON ROSTROS ====================
    
    def insert_face(self, face_data: Dict[str, Any]) -> int:
        """
        Inserta un rostro detectado.
        
        Args:
            face_data: Datos del rostro (embedding, bbox, etc.)
            
        Returns:
            ID del rostro insertado
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        # Serializar embedding
        embedding_blob = pickle.dumps(face_data['embedding'])
        
        cursor.execute("""
            INSERT INTO faces (
                photo_id, person_id, embedding,
                bbox_x, bbox_y, bbox_width, bbox_height, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            face_data['photo_id'],
            face_data.get('person_id'),
            embedding_blob,
            face_data.get('bbox_x'),
            face_data.get('bbox_y'),
            face_data.get('bbox_width'),
            face_data.get('bbox_height'),
            face_data.get('confidence')
        ))
        
        conn.commit()
        face_id = cursor.lastrowid
        logger.debug(f"Rostro insertado con ID: {face_id}")
        return face_id
    
    def get_faces_by_photo(self, photo_id: int) -> List[Dict[str, Any]]:
        """Obtiene todos los rostros de una fotografía"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM faces WHERE photo_id = ?",
            (photo_id,)
        )
        
        faces = []
        for row in cursor.fetchall():
            face_dict = dict(row)
            # Deserializar embedding
            face_dict['embedding'] = pickle.loads(face_dict['embedding'])
            faces.append(face_dict)
        
        return faces
    
    def get_all_face_embeddings(self) -> List[Tuple[int, Any]]:
        """
        Obtiene todos los embeddings faciales para clustering.
        
        Returns:
            Lista de tuplas (face_id, embedding)
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, embedding FROM faces")
        
        embeddings = []
        for row in cursor.fetchall():
            face_id = row['id']
            embedding = pickle.loads(row['embedding'])
            embeddings.append((face_id, embedding))
        
        return embeddings
    
    def update_face_person(self, face_id: int, person_id: int):
        """Asigna un rostro a una persona"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE faces SET person_id = ? WHERE id = ?",
            (person_id, face_id)
        )
        conn.commit()
        logger.debug(f"Rostro ID {face_id} asignado a persona ID {person_id}")
    
    # ==================== OPERACIONES CON ESCENAS ====================
    
    def insert_scene(self, photo_id: int, category: str, confidence: float):
        """Inserta clasificación de escena"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scenes (photo_id, category, confidence)
            VALUES (?, ?, ?)
        """, (photo_id, category, confidence))
        
        conn.commit()
        logger.debug(f"Escena '{category}' insertada para foto ID {photo_id}")
    
    def get_scene(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene la escena clasificada de una foto"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM scenes 
            WHERE photo_id = ? 
            ORDER BY confidence DESC 
            LIMIT 1
        """, (photo_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ==================== OPERACIONES CON ETIQUETAS ====================
    
    def insert_tag(self, photo_id: int, tag_name: str):
        """Inserta una etiqueta personalizada"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO tags (photo_id, tag_name)
                VALUES (?, ?)
            """, (photo_id, tag_name))
            
            conn.commit()
            logger.debug(f"Etiqueta '{tag_name}' añadida a foto ID {photo_id}")
            
        except sqlite3.IntegrityError:
            logger.warning(f"Etiqueta '{tag_name}' ya existe para foto ID {photo_id}")
    
    def get_tags(self, photo_id: int) -> List[str]:
        """Obtiene todas las etiquetas de una foto"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT tag_name FROM tags WHERE photo_id = ?",
            (photo_id,)
        )
        return [row['tag_name'] for row in cursor.fetchall()]
    
    def delete_tag(self, photo_id: int, tag_name: str):
        """Elimina una etiqueta"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM tags WHERE photo_id = ? AND tag_name = ?",
            (photo_id, tag_name)
        )
        conn.commit()
        logger.debug(f"Etiqueta '{tag_name}' eliminada de foto ID {photo_id}")
    
    # ==================== BÚSQUEDAS AVANZADAS ====================
    
    def search_photos(self,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     person_id: Optional[int] = None,
                     scene_category: Optional[str] = None,
                     tags: Optional[List[str]] = None,
                     has_gps: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Busca fotografías según múltiples criterios.
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            person_id: ID de persona
            scene_category: Categoría de escena
            tags: Lista de etiquetas
            has_gps: Si tiene coordenadas GPS
            
        Returns:
            Lista de fotografías que coinciden
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT DISTINCT p.* FROM photos p"
        joins = []
        conditions = []
        params = []
        
        # Join con rostros/personas
        if person_id is not None:
            joins.append("JOIN faces f ON p.id = f.photo_id")
            conditions.append("f.person_id = ?")
            params.append(person_id)
        
        # Join con escenas
        if scene_category is not None:
            joins.append("JOIN scenes s ON p.id = s.photo_id")
            conditions.append("s.category = ?")
            params.append(scene_category)
        
        # Join con etiquetas
        if tags:
            joins.append("JOIN tags t ON p.id = t.photo_id")
            conditions.append(f"t.tag_name IN ({','.join(['?']*len(tags))})")
            params.extend(tags)
        
        # Join con metadatos para GPS
        if has_gps is not None:
            joins.append("JOIN metadata m ON p.id = m.photo_id")
            if has_gps:
                conditions.append("m.gps_latitude IS NOT NULL AND m.gps_longitude IS NOT NULL")
            else:
                conditions.append("m.gps_latitude IS NULL OR m.gps_longitude IS NULL")
        
        # Añadir joins
        query += " " + " ".join(joins)
        
        # Filtros de fecha
        if start_date is not None:
            conditions.append("p.timestamp >= ?")
            params.append(start_date)
        
        if end_date is not None:
            conditions.append("p.timestamp <= ?")
            params.append(end_date)
        
        # Añadir condiciones
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY p.timestamp DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la colección.
        
        Returns:
            Diccionario con estadísticas
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total de fotos
        cursor.execute("SELECT COUNT(*) as total FROM photos")
        stats['total_photos'] = cursor.fetchone()['total']
        
        # Fotos procesadas
        cursor.execute("SELECT COUNT(*) as total FROM photos WHERE processed = 1")
        stats['processed_photos'] = cursor.fetchone()['total']
        
        # Total de personas
        cursor.execute("SELECT COUNT(*) as total FROM persons")
        stats['total_persons'] = cursor.fetchone()['total']
        
        # Total de rostros
        cursor.execute("SELECT COUNT(*) as total FROM faces")
        stats['total_faces'] = cursor.fetchone()['total']
        
        # Fotos con GPS
        cursor.execute("""
            SELECT COUNT(DISTINCT photo_id) as total 
            FROM metadata 
            WHERE gps_latitude IS NOT NULL
        """)
        stats['photos_with_gps'] = cursor.fetchone()['total']
        
        # Distribución por escena
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM scenes 
            GROUP BY category
        """)
        stats['scenes_distribution'] = {
            row['category']: row['count'] 
            for row in cursor.fetchall()
        }
        
        return stats