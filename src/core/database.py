"""
Gestor de base de datos SQLite para la aplicación de organización fotográfica.

Proporciona la interfaz CRUD para fotografías, metadatos, personas y etiquetas.
La deduplicación se basa en el hash MD5 del contenido del archivo, no en la
ruta, lo que detecta duplicados aunque estén en carpetas distintas.
"""
import sqlite3
import logging
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.core.config import DATABASE_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Gestor de base de datos SQLite.

    Proporciona métodos CRUD para fotografías, metadatos EXIF,
    personas detectadas y clasificaciones de escenas.
    """

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_database()

    # ----------------------------------------------------------------
    #  Conexión
    # ----------------------------------------------------------------

    def _ensure_database(self):
        """Crea la base de datos y aplica migraciones si es necesario"""
        self.connect()
        self._create_tables()
        self.close()

    def connect(self) -> sqlite3.Connection:
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path, check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            logger.info(f"Conexión establecida con {self.db_path}")
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    # ----------------------------------------------------------------
    #  Esquema
    # ----------------------------------------------------------------

    def _create_tables(self):
        """Crea las tablas necesarias si no existen"""
        conn = self.connect()
        c = conn.cursor()

        # Fotografías  — UNIQUE en file_hash para deduplicación real
        c.execute("""
            CREATE TABLE IF NOT EXISTS photos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path   TEXT    NOT NULL,
                file_name   TEXT    NOT NULL,
                file_hash   TEXT    UNIQUE,          -- MD5 del contenido
                file_size   INTEGER,
                width       INTEGER,
                height      INTEGER,
                format      TEXT,
                timestamp   DATETIME,
                date_added  DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed   BOOLEAN  DEFAULT 0
            )
        """)

        # Metadatos EXIF
        c.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id        INTEGER NOT NULL,
                camera_make     TEXT,
                camera_model    TEXT,
                focal_length    REAL,
                aperture        REAL,
                exposure_time   TEXT,
                iso             INTEGER,
                flash           INTEGER,
                gps_latitude    REAL,
                gps_longitude   REAL,
                gps_altitude    REAL,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
            )
        """)

        # Personas identificadas por clustering
        c.execute("""
            CREATE TABLE IF NOT EXISTS persons (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT,
                cluster_id   INTEGER NOT NULL,
                date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cluster_id)
            )
        """)

        # Rostros detectados (uno por persona por foto)
        c.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id    INTEGER NOT NULL,
                person_id   INTEGER,
                embedding   BLOB    NOT NULL,
                bbox_x      INTEGER,
                bbox_y      INTEGER,
                bbox_width  INTEGER,
                bbox_height INTEGER,
                confidence  REAL,
                FOREIGN KEY (photo_id)  REFERENCES photos(id)  ON DELETE CASCADE,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL
            )
        """)

        # Escenas clasificadas
        c.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id    INTEGER NOT NULL,
                category    TEXT    NOT NULL,
                confidence  REAL    NOT NULL,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
            )
        """)

        # Etiquetas personalizadas
        c.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_id    INTEGER NOT NULL,
                tag_name    TEXT    NOT NULL,
                date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE,
                UNIQUE(photo_id, tag_name)
            )
        """)

        # Migración inline: agregar file_hash si la BD es anterior a esta versión
        try:
            c.execute("ALTER TABLE photos ADD COLUMN file_hash TEXT")
            conn.commit()
            logger.info("Migración: columna file_hash añadida a photos")
        except sqlite3.OperationalError:
            pass  # ya existe, normal

        # Índices (file_hash ya existe en este punto)
        for ddl in [
            "CREATE INDEX IF NOT EXISTS idx_photos_timestamp  ON photos(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_photos_processed  ON photos(processed)",
            "CREATE INDEX IF NOT EXISTS idx_photos_hash       ON photos(file_hash)",
            "CREATE INDEX IF NOT EXISTS idx_metadata_gps      ON metadata(gps_latitude, gps_longitude)",
            "CREATE INDEX IF NOT EXISTS idx_faces_person      ON faces(person_id)",
            "CREATE INDEX IF NOT EXISTS idx_faces_photo       ON faces(photo_id)",
            "CREATE INDEX IF NOT EXISTS idx_scenes_category   ON scenes(category)",
            "CREATE INDEX IF NOT EXISTS idx_tags_name         ON tags(tag_name)",
        ]:
            c.execute(ddl)

        conn.commit()
        logger.info("Tablas e índices verificados/creados")

    # ----------------------------------------------------------------
    #  Fotografías
    # ----------------------------------------------------------------

    def photo_exists_by_hash(self, file_hash: str) -> Optional[int]:
        """
        Comprueba si una foto con ese hash ya está registrada.

        Args:
            file_hash: Hash MD5 del archivo

        Returns:
            ID de la foto existente, o None si es nueva
        """
        if not file_hash:
            return None
        conn = self.connect()
        row = conn.execute(
            "SELECT id FROM photos WHERE file_hash = ?", (file_hash,)
        ).fetchone()
        return row['id'] if row else None

    def insert_photo(self, photo_data: Dict[str, Any]) -> Optional[int]:
        """
        Inserta una fotografía nueva o devuelve el ID si ya existe.

        La deduplicación se realiza por file_hash (MD5 del contenido).
        Si la foto ya está en BD con ese hash, NO se vuelve a insertar
        ni a reprocesar.

        Args:
            photo_data: Dict con claves file_path, file_name, file_hash, etc.

        Returns:
            ID de la fotografía (existente o recién insertada), o None si error
        """
        conn = self.connect()
        c = conn.cursor()

        file_hash = photo_data.get('file_hash')

        # Verificar por hash primero (deduplicación real por contenido)
        if file_hash:
            existing_id = self.photo_exists_by_hash(file_hash)
            if existing_id is not None:
                logger.debug(
                    f"Duplicado detectado por hash: {photo_data['file_name']} "
                    f"(ID existente: {existing_id})"
                )
                return existing_id  # retorna None-like para que el worker lo omita

        try:
            c.execute("""
                INSERT INTO photos (
                    file_path, file_name, file_hash,
                    file_size, width, height, format, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                photo_data['file_path'],
                photo_data['file_name'],
                file_hash,
                photo_data.get('file_size'),
                photo_data.get('width'),
                photo_data.get('height'),
                photo_data.get('format'),
                photo_data.get('timestamp'),
            ))
            conn.commit()
            photo_id = c.lastrowid
            logger.info(f"Fotografía insertada ID={photo_id}: {photo_data['file_name']}")
            return photo_id

        except sqlite3.IntegrityError:
            # Colisión por file_path o file_hash — buscar por cualquiera
            row = conn.execute(
                "SELECT id FROM photos WHERE file_path = ?",
                (photo_data['file_path'],)
            ).fetchone()
            return row['id'] if row else None

    def get_photo_by_id(self, photo_id: int) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()
        return dict(row) if row else None

    def get_all_photos(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = self.connect()
        query = "SELECT * FROM photos ORDER BY timestamp DESC"
        if limit:
            query += f" LIMIT {limit}"
        return [dict(r) for r in conn.execute(query).fetchall()]

    def get_unprocessed_photos(self) -> List[Dict[str, Any]]:
        conn = self.connect()
        return [dict(r) for r in conn.execute(
            "SELECT * FROM photos WHERE processed = 0"
        ).fetchall()]

    def update_photo_processed(self, photo_id: int):
        conn = self.connect()
        conn.execute("UPDATE photos SET processed = 1 WHERE id = ?", (photo_id,))
        conn.commit()

    def delete_photo(self, photo_id: int):
        """Elimina una foto y sus datos relacionados via ON DELETE CASCADE."""
        conn = self.connect()
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        logger.info(f"Fotografía ID {photo_id} eliminada")

    def search_photos(
        self,
        scene_category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        person_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        conn = self.connect()
        joins, conditions, params = [], [], []

        base = "SELECT DISTINCT p.* FROM photos p"

        if scene_category:
            joins.append("JOIN scenes s ON p.id = s.photo_id")
            conditions.append("s.category = ?")
            params.append(scene_category)
        if person_id is not None:
            joins.append("JOIN faces f ON p.id = f.photo_id")
            conditions.append("f.person_id = ?")
            params.append(person_id)
        if start_date:
            conditions.append("p.timestamp >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("p.timestamp <= ?")
            params.append(end_date)

        query = base
        if joins:
            query += " " + " ".join(joins)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY p.timestamp DESC"
        return [dict(r) for r in conn.execute(query, params).fetchall()]

    # ----------------------------------------------------------------
    #  Metadatos EXIF
    # ----------------------------------------------------------------

    def insert_metadata(self, photo_id: int, metadata: Dict[str, Any]):
        conn = self.connect()
        conn.execute("""
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
            metadata.get('gps_altitude'),
        ))
        conn.commit()

    def get_metadata(self, photo_id: int) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM metadata WHERE photo_id = ?", (photo_id,)
        ).fetchone()
        return dict(row) if row else None

    # ----------------------------------------------------------------
    #  Personas
    # ----------------------------------------------------------------

    def insert_person(self, cluster_id: int, name: Optional[str] = None) -> int:
        conn = self.connect()
        try:
            c = conn.execute(
                "INSERT INTO persons (cluster_id, name) VALUES (?, ?)",
                (cluster_id, name)
            )
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            row = conn.execute(
                "SELECT id FROM persons WHERE cluster_id = ?", (cluster_id,)
            ).fetchone()
            return row['id'] if row else None

    def get_all_persons(self) -> List[Dict[str, Any]]:
        conn = self.connect()
        return [dict(r) for r in conn.execute("""
            SELECT p.*, COUNT(DISTINCT f.photo_id) as photo_count
            FROM persons p
            LEFT JOIN faces f ON p.id = f.person_id
            GROUP BY p.id
            ORDER BY photo_count DESC
        """).fetchall()]

    def get_person_by_id(self, person_id: int) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
        return dict(row) if row else None

    def update_person_name(self, person_id: int, name: str):
        conn = self.connect()
        conn.execute("UPDATE persons SET name = ? WHERE id = ?", (name, person_id))
        conn.commit()

    # ----------------------------------------------------------------
    #  Rostros
    # ----------------------------------------------------------------

    def insert_face(self, face_data: Dict[str, Any]) -> int:
        conn = self.connect()
        embedding_blob = pickle.dumps(face_data['embedding'])
        c = conn.execute("""
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
            face_data.get('confidence'),
        ))
        conn.commit()
        return c.lastrowid

    def get_faces_by_photo(self, photo_id: int) -> List[Dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM faces WHERE photo_id = ?", (photo_id,)
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d['embedding'] = pickle.loads(d['embedding'])
            result.append(d)
        return result

    def get_all_faces_with_embeddings(self) -> List[Dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute("SELECT * FROM faces").fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d['embedding'] = pickle.loads(d['embedding'])
            result.append(d)
        return result

    def get_all_face_embeddings(self) -> List[tuple]:
        """
        Alias de compatibilidad para face_clustering.py.
        Devuelve lista de tuplas (face_id, embedding).
        """
        conn = self.connect()
        rows = conn.execute("SELECT id, embedding FROM faces").fetchall()
        return [(row['id'], pickle.loads(row['embedding'])) for row in rows]

    def update_face_person(self, face_id: int, person_id: int):
        """Alias de compatibilidad para face_clustering.py."""
        self.assign_person_to_face(face_id, person_id)

    def assign_person_to_face(self, face_id: int, person_id: int):
        conn = self.connect()
        conn.execute("UPDATE faces SET person_id = ? WHERE id = ?", (person_id, face_id))
        conn.commit()

    # ----------------------------------------------------------------
    #  Escenas
    # ----------------------------------------------------------------

    def insert_scene(self, photo_id: int, category: str, confidence: float):
        conn = self.connect()
        conn.execute(
            "INSERT INTO scenes (photo_id, category, confidence) VALUES (?, ?, ?)",
            (photo_id, category, confidence)
        )
        conn.commit()

    def get_scene(self, photo_id: int) -> Optional[Dict[str, Any]]:
        conn = self.connect()
        row = conn.execute("""
            SELECT * FROM scenes WHERE photo_id = ?
            ORDER BY confidence DESC LIMIT 1
        """, (photo_id,)).fetchone()
        return dict(row) if row else None

    # ----------------------------------------------------------------
    #  Etiquetas
    # ----------------------------------------------------------------

    def insert_tag(self, photo_id: int, tag_name: str):
        conn = self.connect()
        try:
            conn.execute(
                "INSERT INTO tags (photo_id, tag_name) VALUES (?, ?)",
                (photo_id, tag_name)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # etiqueta duplicada, ignorar

    def get_tags(self, photo_id: int) -> List[str]:
        conn = self.connect()
        return [r['tag_name'] for r in conn.execute(
            "SELECT tag_name FROM tags WHERE photo_id = ?", (photo_id,)
        ).fetchall()]

    def delete_tag(self, photo_id: int, tag_name: str):
        conn = self.connect()
        conn.execute(
            "DELETE FROM tags WHERE photo_id = ? AND tag_name = ?",
            (photo_id, tag_name)
        )
        conn.commit()

    # ----------------------------------------------------------------
    #  Estadísticas
    # ----------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """
        Estadísticas de la colección actualmente almacenada.

        Returns:
            Diccionario con conteos y distribución por escena
        """
        conn = self.connect()
        stats = {}

        stats['total_photos'] = conn.execute(
            "SELECT COUNT(*) FROM photos"
        ).fetchone()[0]

        stats['processed_photos'] = conn.execute(
            "SELECT COUNT(*) FROM photos WHERE processed = 1"
        ).fetchone()[0]

        stats['total_persons'] = conn.execute(
            "SELECT COUNT(*) FROM persons"
        ).fetchone()[0]

        stats['total_faces'] = conn.execute(
            "SELECT COUNT(*) FROM faces"
        ).fetchone()[0]

        stats['photos_with_gps'] = conn.execute(
            "SELECT COUNT(DISTINCT photo_id) FROM metadata WHERE gps_latitude IS NOT NULL"
        ).fetchone()[0]

        rows = conn.execute(
            "SELECT category, COUNT(*) as count FROM scenes GROUP BY category"
        ).fetchall()
        stats['scenes_distribution'] = {r['category']: r['count'] for r in rows}

        return stats

    # ----------------------------------------------------------------
    #  Utilidades de mantenimiento
    # ----------------------------------------------------------------

    def reset_all(self):
        """
        Elimina TODOS los datos de la colección.

        Útil para iniciar con una colección limpia durante desarrollo
        o cuando el usuario desea reimportar desde cero.
        """
        conn = self.connect()
        for table in ('tags', 'scenes', 'faces', 'persons', 'metadata', 'photos'):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM sqlite_sequence")  # reinicia autoincrement
        conn.commit()
        logger.info("Base de datos vaciada completamente")

    def remove_orphans(self):
        """Elimina registros huérfanos (sin foto padre)"""
        conn = self.connect()
        for table in ('metadata', 'faces', 'scenes', 'tags'):
            conn.execute(
                f"DELETE FROM {table} WHERE photo_id NOT IN (SELECT id FROM photos)"
            )
        conn.commit()
        logger.info("Registros huérfanos eliminados")