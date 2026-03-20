"""
Procesador de detección y reconocimiento facial.

Utiliza MTCNN para detección de rostros y FaceNet para extracción
de embeddings faciales. Soporta múltiples rostros por imagen.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from PIL import Image
import torch

# MTCNN y FaceNet ambos de facenet-pytorch (sin dependencia de TensorFlow)
from facenet_pytorch import MTCNN as MTCNN_Detector
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

    Detecta TODOS los rostros presentes en una imagen y extrae
    embeddings faciales individuales para cada uno, permitiendo
    etiquetar múltiples personas por fotografía.
    """

    def __init__(self, device: Optional[str] = None):
        """
        Inicializa el procesador facial.

        Args:
            device: 'cuda' para GPU, 'cpu' para CPU, None para auto-detectar
        """
        # Forzar CPU (DirectML solo para entrenamiento)
        self.device = torch.device('cpu')
        logger.info(f"Usando dispositivo: {self.device}")

        # ── Inicializar detector MTCNN (facenet-pytorch, sin TensorFlow) ──
        try:
            # keep_all=True para detectar MÚLTIPLES rostros por imagen
            # post_process=False para obtener tensores sin normalización adicional
            self.detector = MTCNN_Detector(
                keep_all=True,
                device=self.device,
                post_process=False,
            )
            logger.info("MTCNN (facenet-pytorch) inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando MTCNN: {e}")
            raise

        # ── Inicializar FaceNet para embeddings ─────────────────────
        try:
            self.facenet = InceptionResnetV1(pretrained='vggface2').eval()
            self.facenet = self.facenet.to(self.device)
            logger.info("FaceNet inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando FaceNet: {e}")
            raise

    # ----------------------------------------------------------------
    #  Método principal
    # ----------------------------------------------------------------

    def process_image(self, image_path: Path) -> List[Dict[str, Any]]:
        """
        Procesa una imagen y detecta TODOS los rostros presentes.

        Cada rostro detectado se procesa de forma independiente,
        por lo que una imagen con N personas devuelve N entradas.

        Args:
            image_path: Ruta a la imagen

        Returns:
            Lista de dicts con datos de cada rostro detectado.
            Puede contener 0 o más elementos.
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

        try:
            img = Image.open(image_path).convert('RGB')

            # Advertencia de baja resolución
            if img.size[0] < MIN_IMAGE_RESOLUTION[0] or img.size[1] < MIN_IMAGE_RESOLUTION[1]:
                logger.warning(
                    f"Imagen {image_path.name} tiene resolución baja: {img.size}"
                )

            # Detectar TODOS los rostros
            raw_faces = self._detect_all_faces(img)

            if not raw_faces:
                logger.info(f"Sin rostros en {image_path.name}")
                return []

            logger.info(
                f"{len(raw_faces)} rostro(s) detectado(s) en {image_path.name}"
            )

            # Extraer embedding individual para cada rostro
            results = []
            for idx, face_data in enumerate(raw_faces):
                try:
                    embedding = self.extract_embedding(img, face_data['box'])
                    if embedding is not None:
                        results.append({
                            'bbox_x':      int(face_data['box'][0]),
                            'bbox_y':      int(face_data['box'][1]),
                            'bbox_width':  int(face_data['box'][2]),
                            'bbox_height': int(face_data['box'][3]),
                            'confidence':  float(face_data['confidence']),
                            'embedding':   embedding,
                            'keypoints':   face_data.get('keypoints', {}),
                            'face_index':  idx,   # posición dentro de la imagen
                        })
                        logger.debug(
                            f"Embedding OK para rostro {idx + 1} "
                            f"(conf={face_data['confidence']:.2f})"
                        )
                except Exception as e:
                    logger.warning(f"Error procesando rostro {idx + 1}: {e}")
                    continue

            logger.info(
                f"Embeddings extraídos: {len(results)}/{len(raw_faces)} "
                f"en {image_path.name}"
            )
            return results

        except Exception as e:
            logger.error(f"Error procesando imagen {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return []

    # ----------------------------------------------------------------
    #  Detección de rostros (MTCNN)
    # ----------------------------------------------------------------

    def _detect_all_faces(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Detecta TODOS los rostros en una imagen PIL usando MTCNN de facenet-pytorch.

        facenet_pytorch.MTCNN devuelve (boxes, probs, landmarks) donde:
          - boxes: tensor [N, 4] con coordenadas [x1, y1, x2, y2]
          - probs: tensor [N] con confianzas
          - landmarks: tensor [N, 5, 2] con puntos clave

        Este método convierte el resultado al formato interno
        {box: [x, y, w, h], confidence, keypoints} para mantener
        compatibilidad con el resto del código.

        Args:
            image: Imagen PIL en modo RGB

        Returns:
            Lista de rostros normalizados (0 o más)
        """
        try:
            # detect() devuelve (boxes, probs, landmarks)
            boxes, probs, landmarks = self.detector.detect(image, landmarks=True)

            if boxes is None or len(boxes) == 0:
                return []

            faces = []
            img_w, img_h = image.size

            for i, (box, prob) in enumerate(zip(boxes, probs)):
                confidence = float(prob) if prob is not None else 0.0

                if confidence < FACE_CONFIDENCE_THRESHOLD:
                    logger.debug(
                        f"Rostro descartado: confianza {confidence:.3f} "
                        f"< {FACE_CONFIDENCE_THRESHOLD}"
                    )
                    continue

                # facenet_pytorch devuelve [x1, y1, x2, y2]
                # Convertir a [x, y, width, height]
                x1, y1, x2, y2 = [float(v) for v in box]
                x = max(0, int(x1))
                y = max(0, int(y1))
                w = max(1, int(x2 - x1))
                h = max(1, int(y2 - y1))

                # Convertir landmarks si existen
                kp = {}
                if landmarks is not None and i < len(landmarks):
                    lm = landmarks[i]
                    kp = {
                        'left_eye':    (int(lm[0][0]), int(lm[0][1])),
                        'right_eye':   (int(lm[1][0]), int(lm[1][1])),
                        'nose':        (int(lm[2][0]), int(lm[2][1])),
                        'mouth_left':  (int(lm[3][0]), int(lm[3][1])),
                        'mouth_right': (int(lm[4][0]), int(lm[4][1])),
                    }

                faces.append({
                    'box':        [x, y, w, h],
                    'confidence': confidence,
                    'keypoints':  kp,
                })

            logger.info(
                f"MTCNN: {len(boxes)} detectados, "
                f"{len(faces)} sobre umbral {FACE_CONFIDENCE_THRESHOLD}"
            )
            return faces

        except Exception as e:
            logger.error(f"Error en detección MTCNN: {e}")
            import traceback
            traceback.print_exc()
            return []

    # Alias para mantener compatibilidad con código existente
    def detect_faces(self, image: Image.Image) -> List[Dict[str, Any]]:
        return self._detect_all_faces(image)

    # ----------------------------------------------------------------
    #  Extracción de embeddings (FaceNet)
    # ----------------------------------------------------------------

    def extract_embedding(
        self,
        image: Image.Image,
        bbox: List[int]
    ) -> Optional[np.ndarray]:
        """
        Extrae el embedding facial de UN rostro recortado de la imagen.

        Args:
            image: Imagen PIL completa
            bbox:  Bounding box [x, y, width, height]

        Returns:
            Array numpy con el embedding (512 dims con vggface2) o None
        """
        try:
            x, y, w, h = bbox

            # Añadir margen del 20 %
            margin = 0.20
            x_margin = int(w * margin)
            y_margin = int(h * margin)

            x1 = max(0, x - x_margin)
            y1 = max(0, y - y_margin)
            x2 = min(image.width,  x + w + x_margin)
            y2 = min(image.height, y + h + y_margin)

            if x2 <= x1 or y2 <= y1:
                logger.error(f"Coordenadas de recorte inválidas: {x1},{y1},{x2},{y2}")
                return None

            face = image.crop((x1, y1, x2, y2))

            if face.size[0] == 0 or face.size[1] == 0:
                logger.error("Recorte de rostro vacío")
                return None

            # Redimensionar a 160 × 160 (tamaño esperado por InceptionResnetV1)
            face = face.resize((160, 160), Image.BILINEAR)

            face_array = np.array(face)
            if face_array.size == 0:
                logger.error("Array de rostro vacío")
                return None

            # Convertir a tensor [C, H, W] y normalizar
            face_tensor = torch.from_numpy(face_array).permute(2, 0, 1).float()
            face_tensor = (face_tensor - 127.5) / 128.0
            face_tensor = face_tensor.unsqueeze(0).to(self.device)  # [1, C, H, W]

            with torch.no_grad():
                embedding = self.facenet(face_tensor)

            embedding_np = embedding.cpu().numpy().flatten()
            logger.debug(f"Embedding extraído: {embedding_np.shape[0]} dims")
            return embedding_np

        except Exception as e:
            logger.error(f"Error extrayendo embedding: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ----------------------------------------------------------------
    #  Visualización
    # ----------------------------------------------------------------

    def visualize_detections(
        self,
        image_path: Path,
        faces: List[Dict[str, Any]],
        output_path: Optional[Path] = None
    ) -> np.ndarray:
        """
        Dibuja bounding-boxes sobre todos los rostros detectados.

        Cada rostro recibe un color y número distintos para facilitar
        la identificación cuando hay múltiples personas.

        Args:
            image_path:  Ruta a la imagen original
            faces:       Lista devuelta por process_image()
            output_path: Si se especifica, guarda la imagen anotada

        Returns:
            Array numpy BGR con las anotaciones dibujadas
        """
        img = cv2.imread(str(image_path))
        if img is None:
            logger.error(f"No se pudo cargar imagen: {image_path}")
            return np.array([])

        # Paleta de colores (BGR) para distinguir rostros
        colors = [
            (0, 255, 0),    # verde
            (255, 0, 0),    # azul
            (0, 0, 255),    # rojo
            (0, 255, 255),  # amarillo
            (255, 0, 255),  # magenta
            (255, 165, 0),  # naranja
        ]

        for idx, face in enumerate(faces):
            x  = face['bbox_x']
            y  = face['bbox_y']
            w  = face['bbox_width']
            h  = face['bbox_height']
            conf = face['confidence']

            color = colors[idx % len(colors)]

            # Rectángulo
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)

            # Etiqueta con número de rostro y confianza
            label = f"#{idx + 1} {conf:.0%}"
            label_y = y - 8 if y > 20 else y + h + 20
            cv2.putText(
                img, label, (x, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2
            )

            # Puntos clave faciales (keypoints)
            keypoints = face.get('keypoints', {})
            for kp_name, kp_point in keypoints.items():
                cv2.circle(img, tuple(kp_point), 3, color, -1)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), img)
            logger.info(f"Imagen anotada guardada en: {output_path}")

        return img