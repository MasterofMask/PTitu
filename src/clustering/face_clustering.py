"""
Clustering facial usando DBSCAN.

Agrupa rostros detectados por similitud de embeddings para
identificar automáticamente personas en colecciones fotográficas.
"""
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cosine

from src.core.config import DBSCAN_EPS, DBSCAN_MIN_SAMPLES
from src.core.database import DatabaseManager

logger = logging.getLogger(__name__)


class FaceClustering:
    """
    Clustering facial basado en DBSCAN.
    
    Agrupa embeddings faciales para identificar personas únicas
    en una colección de fotografías.
    """
    
    def __init__(self, 
                 eps: float = DBSCAN_EPS,
                 min_samples: int = DBSCAN_MIN_SAMPLES):
        """
        Inicializa el clustering facial.
        
        Args:
            eps: Radio máximo de vecindad (distancia coseno)
            min_samples: Mínimo de muestras para formar un cluster
        """
        self.eps = eps
        self.min_samples = min_samples
        self.clusterer = None
        self.labels = None
        self.embeddings = None
        self.face_ids = None
    
    def cluster_faces(self, 
                     embeddings: List[np.ndarray],
                     face_ids: List[int]) -> Dict[int, List[int]]:
        """
        Agrupa rostros por similitud de embeddings.
        
        Args:
            embeddings: Lista de embeddings faciales
            face_ids: Lista de IDs de rostros correspondientes
            
        Returns:
            Diccionario {cluster_id: [face_ids]}
        """
        if len(embeddings) == 0:
            logger.warning("No hay embeddings para procesar")
            return {}
        
        if len(embeddings) != len(face_ids):
            raise ValueError("Número de embeddings y face_ids no coincide")
        
        # Guardar referencias
        self.embeddings = np.array(embeddings)
        self.face_ids = face_ids
        
        logger.info(f"Clustering {len(embeddings)} rostros...")
        
        # Aplicar DBSCAN con métrica coseno
        self.clusterer = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric='cosine'
        )
        
        self.labels = self.clusterer.fit_predict(self.embeddings)
        
        # Contar clusters
        n_clusters = len(set(self.labels)) - (1 if -1 in self.labels else 0)
        n_noise = list(self.labels).count(-1)
        
        logger.info(f"Encontrados {n_clusters} clusters y {n_noise} rostros sin clasificar")
        
        # Calcular métrica de calidad si hay suficientes clusters
        if n_clusters > 1 and n_noise < len(self.labels):
            try:
                score = silhouette_score(
                    self.embeddings, 
                    self.labels,
                    metric='cosine'
                )
                logger.info(f"Silhouette score: {score:.3f}")
            except Exception as e:
                logger.debug(f"No se pudo calcular silhouette score: {e}")
        
        # Organizar resultados
        clusters = {}
        for face_id, label in zip(face_ids, self.labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(face_id)
        
        return clusters
    
    def cluster_from_database(self, db: DatabaseManager) -> Dict[int, List[int]]:
        """
        Ejecuta clustering usando rostros almacenados en base de datos.
        
        Args:
            db: Gestor de base de datos
            
        Returns:
            Diccionario {cluster_id: [face_ids]}
        """
        # Obtener embeddings de la base de datos
        data = db.get_all_face_embeddings()
        
        if not data:
            logger.warning("No hay rostros en la base de datos")
            return {}
        
        face_ids = [item[0] for item in data]
        embeddings = [item[1] for item in data]
        
        # Ejecutar clustering
        clusters = self.cluster_faces(embeddings, face_ids)
        
        # Actualizar base de datos con asignaciones
        self._update_database(db, clusters)
        
        return clusters
    
    def _update_database(self, db: DatabaseManager, clusters: Dict[int, List[int]]):
        """
        Actualiza la base de datos con las asignaciones de clustering.
        
        Args:
            db: Gestor de base de datos
            clusters: Diccionario con clusters y rostros
        """
        logger.info("Actualizando base de datos con clusters...")
        
        for cluster_id, face_ids in clusters.items():
            # Saltar ruido (cluster_id = -1)
            if cluster_id == -1:
                logger.info(f"Saltando {len(face_ids)} rostros sin clasificar")
                continue
            
            # Crear o obtener persona para este cluster
            person_id = db.insert_person(cluster_id=cluster_id)
            
            # Asignar rostros a esta persona
            for face_id in face_ids:
                db.update_face_person(face_id, person_id)
            
            logger.debug(f"Cluster {cluster_id}: {len(face_ids)} rostros → Persona ID {person_id}")
        
        logger.info("Base de datos actualizada")
    
    def get_cluster_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del clustering realizado.
        
        Returns:
            Diccionario con estadísticas
        """
        if self.labels is None:
            return {}
        
        unique_labels = set(self.labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        n_noise = list(self.labels).count(-1)
        
        # Tamaño de clusters
        cluster_sizes = {}
        for label in unique_labels:
            if label != -1:
                cluster_sizes[int(label)] = list(self.labels).count(label)
        
        return {
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'n_total': len(self.labels),
            'cluster_sizes': cluster_sizes,
            'parameters': {
                'eps': self.eps,
                'min_samples': self.min_samples
            }
        }
    
    def find_similar_faces(self, 
                          query_embedding: np.ndarray,
                          threshold: float = 0.6) -> List[Tuple[int, float]]:
        """
        Encuentra rostros similares a un embedding dado.
        
        Args:
            query_embedding: Embedding facial de consulta
            threshold: Umbral de similitud (0-1, menor es más similar)
            
        Returns:
            Lista de tuplas (face_id, distancia) ordenadas por similitud
        """
        if self.embeddings is None or self.face_ids is None:
            logger.warning("No hay embeddings cargados")
            return []
        
        # Calcular distancias coseno
        similarities = []
        for i, embedding in enumerate(self.embeddings):
            distance = cosine(query_embedding, embedding)
            if distance <= threshold:
                similarities.append((self.face_ids[i], distance))
        
        # Ordenar por distancia (menor = más similar)
        similarities.sort(key=lambda x: x[1])
        
        return similarities
    
    def optimize_parameters(self,
                           embeddings: List[np.ndarray],
                           eps_range: Tuple[float, float] = (0.4, 0.8),
                           eps_steps: int = 5) -> Dict[str, Any]:
        """
        Busca los mejores parámetros de DBSCAN para el dataset.
        
        Args:
            embeddings: Lista de embeddings
            eps_range: Rango de valores eps a probar
            eps_steps: Número de valores a probar
            
        Returns:
            Diccionario con mejores parámetros y métricas
        """
        if len(embeddings) < 10:
            logger.warning("Dataset muy pequeño para optimización")
            return {}
        
        embeddings_array = np.array(embeddings)
        best_score = -1
        best_params = {}
        
        eps_values = np.linspace(eps_range[0], eps_range[1], eps_steps)
        
        logger.info("Optimizando parámetros de clustering...")
        
        for eps in eps_values:
            clusterer = DBSCAN(
                eps=eps,
                min_samples=self.min_samples,
                metric='cosine'
            )
            
            labels = clusterer.fit_predict(embeddings_array)
            
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)
            
            # Evaluar solo si hay clusters válidos
            if n_clusters > 1 and n_noise < len(labels) * 0.5:
                try:
                    score = silhouette_score(
                        embeddings_array,
                        labels,
                        metric='cosine'
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_params = {
                            'eps': eps,
                            'min_samples': self.min_samples,
                            'n_clusters': n_clusters,
                            'n_noise': n_noise,
                            'silhouette_score': score
                        }
                
                except Exception as e:
                    logger.debug(f"Error calculando score para eps={eps}: {e}")
                    continue
        
        if best_params:
            logger.info(f"Mejores parámetros encontrados: eps={best_params['eps']:.3f}, "
                       f"score={best_params['silhouette_score']:.3f}")
        else:
            logger.warning("No se encontraron parámetros óptimos")
        
        return best_params