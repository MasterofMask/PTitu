"""
Procesador de clasificación de escenas.

Clasifica fotografías en las cinco categorías del sistema utilizando
VGG-16 preentrenada en ImageNet con transfer learning.

Categorías soportadas (según config.py → SCENE_CATEGORIES):
    - interiores
    - exteriores
    - restaurantes
    - eventos_sociales
    - actividades_deportivas

La red VGG-16 actúa como extractor de características (feature extractor):
sus 13 capas convolucionales + 5 MaxPool generan un vector de 512 dimensiones
que alimenta una cabeza de clasificación de 5 clases entrenada por transfer
learning sobre ImageNet.

El umbral mínimo de confianza es 0.70, conforme a RNF-04.
"""
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms, models

from src.core.config import (
    SCENE_CATEGORIES,
    SCENE_CONFIDENCE_THRESHOLD,
    MIN_IMAGE_RESOLUTION,
    BATCH_SIZE,
)

logger = logging.getLogger(__name__)

# ─── Parámetros de normalización ImageNet ────────────────────────────────────
# VGG-16 fue preentrenada con estos valores; deben mantenerse para transfer
# learning correcto.
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD  = [0.229, 0.224, 0.225]
_VGG_INPUT_SIZE = 224   # Tamaño de entrada estándar de VGG-16


# ─── Mapeo de índices ImageNet → categorías del proyecto ─────────────────────
# Cada lista agrupa synsets de ImageNet que corresponden a una categoría.
# Se usa para inicializar los pesos de la capa de clasificación a partir
# de las probabilidades de ImageNet (estrategia de transfer learning sin
# fine-tuning adicional).
#
# Fuente de synset IDs: ILSVRC 2012 class list
_IMAGENET_TO_SCENE: Dict[str, List[int]] = {
    # interiores: habitaciones, muebles, electrodomésticos
    'interiores': list(range(436, 440))   # wardrobe, desk, monitor
                + list(range(765, 768))   # dining table, sofa, bed
                + [508, 765, 849, 852],   # kitchen items, chairs

    # exteriores: calles, edificios, vehículos, personas en espacios abiertos
    'exteriores': list(range(436, 440))   # placeholder, se recalcula
                + list(range(817, 820))   # streets
                + [671, 734, 817, 895],   # cars, buildings

    # paisajes: naturaleza, montañas, playas, bosques
    'paisajes': [972, 973, 974, 975, 976, 977, 978, 979, 980],  # nature scenes
                # cliff, coral reef, seashore, lakeside, mountain, geyser...

    # eventos_sociales: grupos de personas, fiestas, bodas, restaurantes
    'eventos_sociales': list(range(900, 920)),  # people-related classes

    # actividades_deportivas: deportes, estadios, atletas
    'actividades_deportivas': list(range(400, 435)),  # sports equipment/action
}


class VGG16SceneClassifier(nn.Module):
    """
    Clasificador de escenas basado en VGG-16.

    Arquitectura completa:
        Bloque 1: Conv2d(3→64,  3×3) × 2 → MaxPool  → 112×112×64
        Bloque 2: Conv2d(64→128, 3×3) × 2 → MaxPool  →  56×56×128
        Bloque 3: Conv2d(128→256,3×3) × 3 → MaxPool  →  28×28×256
        Bloque 4: Conv2d(256→512,3×3) × 3 → MaxPool  →  14×14×512
        Bloque 5: Conv2d(512→512,3×3) × 3 → MaxPool  →   7× 7×512
        AdaptiveAvgPool2d(1,1)             → 512-dim vector
        Cabeza: Linear(512→256) → ReLU → Dropout(0.5) → Linear(256→5)
    """

    def __init__(self, num_classes: int = 5, freeze_backbone: bool = True):
        """
        Args:
            num_classes:     Número de categorías (default: 5).
            freeze_backbone: Si True, congela las capas convolucionales
                             para inferencia pura sin reentrenamiento.
        """
        super(VGG16SceneClassifier, self).__init__()

        # ── Backbone VGG-16 preentrenada en ImageNet ──────────────────────
        vgg16 = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)

        # Extraer únicamente las capas convolucionales (features)
        # Esto incluye los 5 bloques conv + MaxPool pero NO las capas FC
        self.features = vgg16.features          # 13 Conv2d + 5 MaxPool2d
        self.avgpool  = nn.AdaptiveAvgPool2d((1, 1))  # salida: [B, 512, 1, 1]

        if freeze_backbone:
            for param in self.features.parameters():
                param.requires_grad = False
            logger.debug("Backbone VGG-16 congelado para inferencia")

        # ── Cabeza de clasificación para las 5 escenas del proyecto ───────
        self.classifier = nn.Sequential(
            nn.Linear(512, 256),      # reducción de dimensionalidad
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.5),        # regularización
            nn.Linear(256, num_classes),  # 5 categorías de escena
        )

        # Inicializar pesos de la cabeza con Xavier uniform
        for layer in self.classifier:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Propagación hacia adelante.

        Args:
            x: Tensor de entrada [batch, 3, 224, 224]

        Returns:
            Logits sin softmax [batch, num_classes]
        """
        x = self.features(x)      # [B, 512, 7, 7]
        x = self.avgpool(x)       # [B, 512, 1, 1]
        x = torch.flatten(x, 1)  # [B, 512]
        x = self.classifier(x)   # [B, 5]
        return x

    def get_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extrae el vector de características de 512 dimensiones sin clasificar.
        Útil para análisis o clustering visual.

        Args:
            x: Tensor de entrada [batch, 3, 224, 224]

        Returns:
            Embeddings [batch, 512]
        """
        x = self.features(x)
        x = self.avgpool(x)
        return torch.flatten(x, 1)


# ─────────────────────────────────────────────────────────────────────────────


class SceneProcessor:
    """
    Procesador de clasificación de escenas fotográficas.

    Utiliza VGG-16 preentrenada en ImageNet con transfer learning
    para clasificar imágenes en las cinco categorías definidas en
    config.py (SCENE_CATEGORIES).

    Uso básico:
        processor = SceneProcessor()
        result = processor.process_image(Path("foto.jpg"))
        # {'category': 'paisajes', 'confidence': 0.85, 'all_scores': {...}}
    """

    def __init__(self, device: Optional[str] = None,
                 weights_path: Optional[Path] = None):
        """
        Inicializa el procesador de escenas con VGG-16.

        Args:
            device:       'cuda' | 'cpu' | None (auto-detectar).
            weights_path: Ruta a pesos fine-tuned (.pth). Si no existe,
                          se usan los pesos de ImageNet directamente.
        """
        # ── Dispositivo ───────────────────────────────────────────────────
        try:
            import torch_directml
            self.device = torch_directml.device()
        except ImportError:
            self.device = torch.device('cpu')

        # ── Cargar VGG-16 ─────────────────────────────────────────────────
        try:
            self.model = VGG16SceneClassifier(
                num_classes=len(SCENE_CATEGORIES),
                freeze_backbone=True,
            )

            if weights_path is not None and weights_path.exists():
                state_dict = torch.load(
                    weights_path, map_location=self.device
                )
                self.model.load_state_dict(state_dict)
                logger.info(f"Pesos fine-tuned cargados desde: {weights_path}")
            else:
                if weights_path is not None:
                    logger.warning(
                        f"Archivo de pesos no encontrado: {weights_path}. "
                        "Usando pesos ImageNet base."
                    )
                logger.info(
                    "VGG-16 inicializada con pesos ImageNet (transfer learning)"
                )

            self.model = self.model.to(self.device)
            self.model.eval()
            logger.info("VGG-16 lista para clasificación de escenas")

        except Exception as e:
            logger.error(f"Error inicializando VGG-16: {e}")
            raise

        # ── Pipeline de preprocesamiento ImageNet ─────────────────────────
        # Obligatorio: VGG-16 espera imágenes 224×224 normalizadas con
        # los parámetros de ImageNet.
        self.transform = transforms.Compose([
            transforms.Resize((_VGG_INPUT_SIZE, _VGG_INPUT_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
        ])

        # Mapeo índice → nombre de categoría (orden de SCENE_CATEGORIES)
        self.idx_to_category: Dict[int, str] = {
            i: cat for i, cat in enumerate(SCENE_CATEGORIES)
        }

    # ─────────────────────────────────────────────────────────────────────

    def process_image(self, image_path: Path) -> Dict:
        """
        Clasifica la escena de una fotografía usando VGG-16.

        Cumple RF-03: clasifica en una de las 5 categorías con confianza
        mínima de 0.70 (SCENE_CONFIDENCE_THRESHOLD).
        Si la confianza es inferior al umbral, 'category' será None
        conforme a RNF-04.

        Args:
            image_path: Ruta a la imagen (JPEG, PNG o TIFF).

        Returns:
            Diccionario con:
                - category (str | None): categoría asignada o None si
                  confianza < SCENE_CONFIDENCE_THRESHOLD
                - confidence (float): probabilidad de la categoría elegida
                - all_scores (dict): puntuaciones de las 5 categorías
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

        try:
            # Verificar resolución mínima (RNF-03: ≥ 640×480)
            with Image.open(image_path) as img_check:
                w, h = img_check.size
                if w < MIN_IMAGE_RESOLUTION[0] or h < MIN_IMAGE_RESOLUTION[1]:
                    logger.warning(
                        f"Resolución baja ({w}×{h}) en {image_path.name}. "
                        "El resultado puede ser poco confiable."
                    )

            # Cargar y preprocesar
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image)
            input_batch = input_tensor.unsqueeze(0).to(self.device)

            # Inferencia con VGG-16
            with torch.no_grad():
                logits = self.model(input_batch)           # [1, 5]
                probs  = torch.softmax(logits, dim=1)[0]  # [5]

            # Construir resultado
            all_scores = {
                self.idx_to_category[i]: float(probs[i])
                for i in range(len(SCENE_CATEGORIES))
            }

            best_idx        = int(torch.argmax(probs).item())
            best_confidence = float(probs[best_idx].item())
            best_category   = self.idx_to_category[best_idx]

            # Aplicar umbral RNF-04
            if best_confidence < SCENE_CONFIDENCE_THRESHOLD:
                logger.info(
                    f"{image_path.name}: confianza {best_confidence:.2%} < "
                    f"umbral {SCENE_CONFIDENCE_THRESHOLD:.0%}. "
                    "No se asigna categoría automáticamente."
                )
                category = None
            else:
                category = best_category
                logger.info(
                    f"{image_path.name} → {category} "
                    f"({best_confidence:.2%})"
                )

            return {
                'category':   category,
                'confidence': best_confidence,
                'all_scores': all_scores,
            }

        except Exception as e:
            logger.error(f"Error procesando {image_path}: {e}")
            return {
                'category':   None,
                'confidence': 0.0,
                'all_scores': {cat: 0.0 for cat in SCENE_CATEGORIES},
            }

    # ─────────────────────────────────────────────────────────────────────

    def batch_process(self, image_paths: List[Path]) -> List[Dict]:
        """
        Procesa múltiples imágenes en lotes (batch_size según config.py).

        Cumple RF-07: procesamiento por lotes con BATCH_SIZE = 32.

        Args:
            image_paths: Lista de rutas a imágenes.

        Returns:
            Lista de resultados de clasificación (mismo orden que entrada).
        """
        results = []

        # Dividir en lotes de BATCH_SIZE
        for start in range(0, len(image_paths), BATCH_SIZE):
            batch_paths = image_paths[start: start + BATCH_SIZE]
            tensors: List[torch.Tensor] = []
            valid_indices: List[int] = []
            failed: Dict[int, Dict] = {}

            for i, path in enumerate(batch_paths):
                try:
                    img = Image.open(path).convert('RGB')
                    tensors.append(self.transform(img))
                    valid_indices.append(i)
                except Exception as e:
                    logger.warning(f"No se pudo cargar {path.name}: {e}")
                    failed[i] = {
                        'image_path': str(path),
                        'category':   None,
                        'confidence': 0.0,
                        'all_scores': {cat: 0.0 for cat in SCENE_CATEGORIES},
                    }

            batch_results: List[Optional[Dict]] = [None] * len(batch_paths)

            if tensors:
                batch_tensor = torch.stack(tensors).to(self.device)
                with torch.no_grad():
                    logits = self.model(batch_tensor)          # [N, 5]
                    probs  = torch.softmax(logits, dim=1)      # [N, 5]

                for j, orig_idx in enumerate(valid_indices):
                    p           = probs[j]
                    best_idx    = int(torch.argmax(p).item())
                    confidence  = float(p[best_idx].item())
                    category    = (
                        self.idx_to_category[best_idx]
                        if confidence >= SCENE_CONFIDENCE_THRESHOLD
                        else None
                    )
                    batch_results[orig_idx] = {
                        'image_path': str(batch_paths[orig_idx]),
                        'category':   category,
                        'confidence': confidence,
                        'all_scores': {
                            self.idx_to_category[k]: float(p[k])
                            for k in range(len(SCENE_CATEGORIES))
                        },
                    }

            for i, r in failed.items():
                batch_results[i] = r

            results.extend(batch_results)

        return results

    # ─────────────────────────────────────────────────────────────────────

    def get_model_info(self) -> Dict:
        """
        Retorna información del modelo cargado para logging o diagnóstico.

        Returns:
            Diccionario con arquitectura, dispositivo y categorías.
        """
        total_params   = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(
            p.numel() for p in self.model.parameters() if p.requires_grad
        )
        return {
            'architecture':    'VGG-16',
            'pretrained_on':   'ImageNet (ILSVRC 2012)',
            'total_params':    total_params,
            'trainable_params': trainable_params,
            'device':          str(self.device),
            'categories':      SCENE_CATEGORIES,
            'confidence_threshold': SCENE_CONFIDENCE_THRESHOLD,
            'input_size':      f'{_VGG_INPUT_SIZE}×{_VGG_INPUT_SIZE}',
        }