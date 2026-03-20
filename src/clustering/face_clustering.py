"""
Clustering facial usando DBSCAN.

Agrupa rostros detectados por similitud de embeddings. Si una persona
ya fue etiquetada manualmente, sus embeddings se usan como semillas para
asignar automáticamente rostros nuevos a la misma persona.
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cosine

from src.core.config import DBSCAN_EPS, DBSCAN_MIN_SAMPLES
from src.core.database import DatabaseManager

logger = logging.getLogger(__name__)

# Umbral de similitud coseno para asignar un rostro nuevo a una
# persona ya etiquetada manualmente (menor = más estricto).
MANUAL_LABEL_THRESHOLD = 0.45


class FaceClustering:
    """
    Clustering facial basado en DBSCAN con soporte de etiquetas manuales.

    Flujo al llamar cluster_from_database():
      1. Separa rostros ya etiquetados manualmente de los sin etiquetar.
      2. Calcula el centroide de embeddings por persona etiquetada.
      3. Para cada rostro sin etiquetar, calcula distancia coseno a cada
         centroide. Si está dentro del umbral, asigna a esa persona.
      4. Los rostros restantes pasan por DBSCAN para formar grupos nuevos.
      5. Los nuevos clusters reciben person_id nuevos (sin nombre).
    """

    def __init__(self,
                 eps: float = DBSCAN_EPS,
                 min_samples: int = DBSCAN_MIN_SAMPLES):
        self.eps = eps
        self.min_samples = min_samples
        self.clusterer = None
        self.labels = None
        self.embeddings = None
        self.face_ids = None

    # ----------------------------------------------------------------
    #  Punto de entrada principal
    # ----------------------------------------------------------------

    def cluster_from_database(self, db: DatabaseManager) -> Dict[int, List[int]]:
        """
        Ejecuta clustering completo respetando etiquetas manuales.

        Args:
            db: Gestor de base de datos

        Returns:
            Diccionario {cluster_id: [face_ids]}
        """
        all_data = db.get_all_face_embeddings()
        if not all_data:
            logger.warning("No hay rostros en la base de datos")
            return {}

        # ── 1. Separar etiquetados y sin etiquetar ───────────────────
        conn = db.connect()
        labeled_faces = {}    # person_id → [(face_id, embedding)]
        unlabeled = []        # [(face_id, embedding)]

        for face_id, embedding in all_data:
            row = conn.execute(
                "SELECT person_id FROM faces WHERE id = ?", (face_id,)
            ).fetchone()
            pid = row['person_id'] if row else None

            if pid is not None:
                # Verificar que la persona tiene nombre (etiquetada manualmente)
                person = db.get_person_by_id(pid)
                if person and person.get('name'):
                    labeled_faces.setdefault(pid, []).append((face_id, embedding))
                    continue
            unlabeled.append((face_id, embedding))

        logger.info(
            f"Rostros etiquetados: {sum(len(v) for v in labeled_faces.values())}, "
            f"sin etiquetar: {len(unlabeled)}"
        )

        # ── 2. Centroides por persona etiquetada ─────────────────────
        centroids: Dict[int, np.ndarray] = {}
        for pid, items in labeled_faces.items():
            embs = np.array([e for _, e in items])
            centroids[pid] = embs.mean(axis=0)

        # ── 3. Asignar rostros sin etiquetar a personas conocidas ─────
        still_unlabeled = []
        assigned_to_known = 0

        for face_id, embedding in unlabeled:
            best_pid, best_dist = None, float('inf')
            for pid, centroid in centroids.items():
                dist = cosine(embedding, centroid)
                if dist < best_dist:
                    best_dist = dist
                    best_pid = pid

            if best_pid is not None and best_dist <= MANUAL_LABEL_THRESHOLD:
                db.update_face_person(face_id, best_pid)
                # Actualizar centroide con este embedding nuevo
                old = centroids[best_pid]
                n = len(labeled_faces[best_pid]) + assigned_to_known + 1
                centroids[best_pid] = old + (embedding - old) / n
                assigned_to_known += 1
            else:
                still_unlabeled.append((face_id, embedding))

        logger.info(
            f"Asignados a personas conocidas: {assigned_to_known}, "
            f"aún sin etiquetar: {len(still_unlabeled)}"
        )

        # ── 4. DBSCAN sobre los rostros restantes ─────────────────────
        clusters: Dict[int, List[int]] = {}
        if still_unlabeled:
            face_ids_u = [fid for fid, _ in still_unlabeled]
            embeddings_u = [emb for _, emb in still_unlabeled]
            clusters = self.cluster_faces(embeddings_u, face_ids_u)
            self._update_database(db, clusters)

        return clusters

    # ----------------------------------------------------------------
    #  DBSCAN puro
    # ----------------------------------------------------------------

    def cluster_faces(self,
                      embeddings: List[np.ndarray],
                      face_ids: List[int]) -> Dict[int, List[int]]:
        """
        Agrupa rostros por similitud de embeddings con DBSCAN.

        Args:
            embeddings: Lista de embeddings faciales
            face_ids:   IDs correspondientes a cada embedding

        Returns:
            {cluster_label: [face_ids]}
        """
        if not embeddings:
            return {}

        self.embeddings = np.array(embeddings)
        self.face_ids = face_ids

        self.clusterer = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='cosine'
        )
        self.labels = self.clusterer.fit_predict(self.embeddings)

        n_clusters = len(set(self.labels)) - (1 if -1 in self.labels else 0)
        n_noise    = list(self.labels).count(-1)
        logger.info(f"DBSCAN: {n_clusters} cluster(s), {n_noise} ruido(s)")

        if n_clusters > 1 and n_noise < len(self.labels):
            try:
                score = silhouette_score(self.embeddings, self.labels,
                                         metric='cosine')
                logger.info(f"Silhouette score: {score:.3f}")
            except Exception:
                pass

        clusters: Dict[int, List[int]] = {}
        for fid, lbl in zip(face_ids, self.labels):
            clusters.setdefault(lbl, []).append(fid)
        return clusters

    # ----------------------------------------------------------------
    #  Actualización en BD para clusters DBSCAN nuevos
    # ----------------------------------------------------------------

    def _next_desconocido_name(self, db: DatabaseManager) -> str:
        """
        Genera el siguiente nombre disponible en la serie
        'Desconocido', 'Desconocido 2', 'Desconocido 3', ...
        """
        persons = db.get_all_persons()
        existing_names = {p.get('name') or '' for p in persons}

        if 'Desconocido' not in existing_names:
            return 'Desconocido'

        n = 2
        while True:
            candidate = f'Desconocido {n}'
            if candidate not in existing_names:
                return candidate
            n += 1

    def _safe_max_cluster_id(self, db: DatabaseManager) -> int:
        """
        Calcula el cluster_id máximo existente de forma segura,
        convirtiendo bytes corruptos antes de comparar.
        """
        conn = db.connect()
        rows = conn.execute("SELECT cluster_id FROM persons").fetchall()
        max_id = 9000
        for r in rows:
            try:
                cid = r['cluster_id']
                if isinstance(cid, (bytes, bytearray)):
                    cid = int.from_bytes(cid[:4], 'little')
                val = int(cid)
                if val > max_id:
                    max_id = val
            except (TypeError, ValueError):
                pass
        return max_id

    def _update_database(self, db: DatabaseManager,
                         clusters: Dict[int, List[int]]):
        """
        Crea personas nuevas con nombre 'Desconocido / Desconocido N'
        para los clusters DBSCAN que no pudieron asignarse a nadie conocido.
        El cluster_id siempre se guarda como int puro.
        """
        offset = self._safe_max_cluster_id(db)

        for cluster_label, face_ids in clusters.items():
            if cluster_label == -1:
                logger.debug(f"Ruido DBSCAN: {len(face_ids)} rostro(s) sin asignar")
                continue

            # cluster_id como int puro para evitar que SQLite lo guarde como bytes
            new_cluster_id = int(offset + cluster_label + 1)

            # Nombre legible en lugar de "Persona XXXX"
            auto_name = self._next_desconocido_name(db)

            person_id = db.insert_person(cluster_id=new_cluster_id, name=auto_name)
            for fid in face_ids:
                db.update_face_person(fid, person_id)
            logger.info(
                f"Cluster {cluster_label} → '{auto_name}' "
                f"(ID {person_id}, {len(face_ids)} rostros)"
            )

    # ----------------------------------------------------------------
    #  Estadísticas
    # ----------------------------------------------------------------

    def get_cluster_statistics(self) -> Dict[str, Any]:
        if self.labels is None:
            return {'n_clusters': 0, 'n_noise': 0, 'n_total': 0,
                    'cluster_sizes': {}, 'parameters': {
                        'eps': self.eps, 'min_samples': self.min_samples}}

        unique = set(self.labels)
        n_clusters = len(unique) - (1 if -1 in unique else 0)
        n_noise    = list(self.labels).count(-1)

        sizes = {
            int(lbl): list(self.labels).count(lbl)
            for lbl in unique if lbl != -1
        }
        return {
            'n_clusters':   n_clusters,
            'n_noise':      n_noise,
            'n_total':      len(self.labels),
            'cluster_sizes': sizes,
            'parameters':   {'eps': self.eps, 'min_samples': self.min_samples}
        }

    # ----------------------------------------------------------------
    #  Búsqueda de similares
    # ----------------------------------------------------------------

    def find_similar_faces(self, query_embedding: np.ndarray,
                           threshold: float = 0.6) -> List[Tuple[int, float]]:
        if self.embeddings is None or self.face_ids is None:
            return []
        results = [
            (self.face_ids[i], cosine(query_embedding, emb))
            for i, emb in enumerate(self.embeddings)
            if cosine(query_embedding, emb) <= threshold
        ]
        return sorted(results, key=lambda x: x[1])