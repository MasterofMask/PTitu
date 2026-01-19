"""
Procesador de detección y reconocimiento facial.

Utiliza MTCNN para detección de rostros y FaceNet para extracción
de embeddings faciales de 128 dimensiones.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from PIL import Image
import torch

# Importar MTCNN (versión mtcnn package, no facenet-pytorch)
from mtcnn import MTCNN as MTCNN_Detector

# Importar FaceNet de facenet-pytorch
from facenet_pytorch import InceptionResnetV1

from src.core.config import (
    FACE_CONFIDENCE_THRESHOLD,
    FACE_EMBEDDING_SIZE,
    MIN_IMAGE_RESOLUTION
)

logger = logging.getLogger(__name__)


class FaceProcessor:
    """
    Procesador de detección y reconocimiento facial.
    
    Detecta rostros en imágenes y extrae embeddings faciales
    para posterior clustering y reconocimiento.
    """
    
    def __init__(self, device: Optional[str] = None):
        """
        Inicializa el procesador facial.
        
        Args:
            device: 'cuda' para GPU, 'cpu' para CPU, None para auto-detectar
        """
        # Determinar dispositivo
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        logger.info(f"Usando dispositivo: {self.device}")
        
        # Inicializar detector MTCNN (versión estándar)
        try:
            self.detector = MTCNN_Detector()
            logger.info("MTCNN inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando MTCNN: {e}")
            raise
        
        # Inicializar FaceNet para embeddings
        try:
            self.facenet = InceptionResnetV1(pretrained='vggface2').eval()
            self.facenet = self.facenet.to(self.device)
            logger.info("FaceNet inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando FaceNet: {e}")
            raise
    
    def process_image(self, image_path: Path) -> List[Dict[str, Any]]:
        """
        Procesa una imagen y detecta todos los rostros.
        
        Args:
            image_path: Ruta a la imagen
            
        Returns:
            Lista de diccionarios con datos de rostros detectados
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")
        
        try:
            # Cargar imagen
            img = Image.open(image_path).convert('RGB')
            
            # Verificar resolución mínima
            if img.size[0] < MIN_IMAGE_RESOLUTION[0] or img.size[1] < MIN_IMAGE_RESOLUTION[1]:
                logger.warning(
                    f"Imagen {image_path.name} tiene resolución muy baja: {img.size}"
                )
            
            # Detectar rostros
            faces = self.detect_faces(img)
            
            if not faces:
                logger.info(f"No se detectaron rostros en {image_path.name}")
                return []
            
            logger.info(f"Detectados {len(faces)} rostro(s) en {image_path.name}")
            
            # Extraer embeddings para cada rostro
            results = []
            for i, face_data in enumerate(faces):
                try:
                    # Obtener embedding
                    embedding = self.extract_embedding(img, face_data['box'])
                    
                    if embedding is not None:
                        results.append({
                            'bbox_x': int(face_data['box'][0]),
                            'bbox_y': int(face_data['box'][1]),
                            'bbox_width': int(face_data['box'][2]),
                            'bbox_height': int(face_data['box'][3]),
                            'confidence': float(face_data['confidence']),
                            'embedding': embedding,
                            'keypoints': face_data.get('keypoints')
                        })
                        logger.debug(f"Embedding extraído para rostro {i+1}")
                    
                except Exception as e:
                    logger.warning(f"Error procesando rostro {i+1}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error procesando imagen {image_path}: {e}")
            return []
    
    def detect_faces(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Detecta rostros en una imagen usando MTCNN.
        
        Args:
            image: Imagen PIL
            
        Returns:
            Lista de rostros detectados con bboxes y confianza
        """
        try:
            # Convertir a array numpy (RGB)
            img_array = np.array(image)
            
            # Detectar rostros (MTCNN devuelve BGR, pero recibe RGB)
            detections = self.detector.detect_faces(img_array)
            
            if not detections:
                return []
            
            # Filtrar por confianza
            faces = []
            for detection in detections:
                confidence = detection['confidence']
                
                if confidence >= FACE_CONFIDENCE_THRESHOLD:
                    # MTCNN devuelve box como [x, y, width, height]
                    box = detection['box']
                    
                    # Asegurar que las coordenadas sean válidas
                    x, y, w, h = box
                    x = max(0, x)
                    y = max(0, y)
                    w = max(1, w)
                    h = max(1, h)
                    
                    faces.append({
                        'box': [x, y, w, h],
                        'confidence': confidence,
                        'keypoints': detection.get('keypoints', {})
                    })
            
            logger.info(f"Detectados {len(faces)} rostros con confianza >= {FACE_CONFIDENCE_THRESHOLD}")
            
            return faces
            
        except Exception as e:
            logger.error(f"Error en detección de rostros: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def extract_embedding(self, 
                         image: Image.Image, 
                         bbox: List[int]) -> Optional[np.ndarray]:
        """
        Extrae embedding facial de un rostro detectado.
        
        Args:
            image: Imagen PIL completa
            bbox: Bounding box [x, y, width, height]
            
        Returns:
            Array numpy con embedding de 128 o 512 dimensiones o None
        """
        try:
            # Extraer región del rostro con margen
            x, y, w, h = bbox
            
            # Añadir margen del 20%
            margin = 0.2
            x_margin = int(w * margin)
            y_margin = int(h * margin)
            
            x1 = max(0, x - x_margin)
            y1 = max(0, y - y_margin)
            x2 = min(image.width, x + w + x_margin)
            y2 = min(image.height, y + h + y_margin)
            
            # Verificar que las coordenadas sean válidas
            if x2 <= x1 or y2 <= y1:
                logger.error(f"Coordenadas de recorte inválidas: ({x1}, {y1}, {x2}, {y2})")
                return None
            
            # Recortar rostro
            face = image.crop((x1, y1, x2, y2))
            
            # Verificar que el recorte no esté vacío
            if face.size[0] == 0 or face.size[1] == 0:
                logger.error("Rostro recortado está vacío")
                return None
            
            # Redimensionar a 160x160 (tamaño esperado por FaceNet)
            face = face.resize((160, 160), Image.BILINEAR)
            
            # Convertir a tensor
            face_array = np.array(face)
            
            # Verificar que no esté vacío
            if face_array.size == 0:
                logger.error("Array de rostro está vacío")
                return None
            
            face_tensor = torch.from_numpy(face_array).permute(2, 0, 1).float()
            
            # Normalizar (mean=127.5, std=128.0)
            face_tensor = (face_tensor - 127.5) / 128.0
            
            # Añadir dimensión de batch
            face_tensor = face_tensor.unsqueeze(0).to(self.device)
            
            # Extraer embedding
            with torch.no_grad():
                embedding = self.facenet(face_tensor)
            
            # Convertir a numpy
            embedding = embedding.cpu().numpy().flatten()
            
            # El embedding de FaceNet puede ser de 512 dimensiones
            # Lo normalizamos a 128 si es necesario (o dejamos 512)
            logger.debug(f"Embedding extraído con dimensión: {embedding.shape[0]}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error extrayendo embedding: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def visualize_detections(self, 
                            image_path: Path, 
                            faces: List[Dict[str, Any]],
                            output_path: Optional[Path] = None) -> np.ndarray:
        """
        Visualiza las detecciones de rostros en la imagen.
        
        Args:
            image_path: Ruta a la imagen original
            faces: Lista de rostros detectados
            output_path: Ruta para guardar la imagen (opcional)
            
        Returns:
            Imagen con rostros marcados
        """
        # Cargar imagen con OpenCV
        img = cv2.imread(str(image_path))
        
        if img is None:
            logger.error(f"No se pudo cargar la imagen: {image_path}")
            return np.array([])
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Dibujar cada rostro
        for i, face in enumerate(faces):
            x = face['bbox_x']
            y = face['bbox_y']
            w = face['bbox_width']
            h = face['bbox_height']
            conf = face['confidence']
            
            # Dibujar rectángulo
            color = (0, 255, 0)  # Verde
            thickness = 3
            cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)
            
            # Añadir texto con confianza
            label = f"Rostro {i+1}: {conf:.2%}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2
            
            # Fondo para el texto
            (text_width, text_height), _ = cv2.getTextSize(
                label, font, font_scale, font_thickness
            )
            cv2.rectangle(
                img, 
                (x, y - text_height - 10), 
                (x + text_width, y), 
                color, 
                -1
            )
            
            # Texto
            cv2.putText(
                img, label, (x, y - 5),
                font, font_scale, (0, 0, 0), font_thickness
            )
        
        # Guardar si se especifica ruta
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            logger.info(f"Visualización guardada en {output_path}")
        
        return img