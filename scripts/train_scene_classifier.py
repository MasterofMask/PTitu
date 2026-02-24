"""
Fine-tuning de VGG-16 para clasificación de escenas.

Entrena la cabeza de clasificación de VGG-16 usando el dataset
descargado por prepare_dataset.py, conservando el backbone
convolucional congelado (transfer learning).

Uso:
    cd raiz_del_proyecto
    python scripts/train_scene_classifier.py

Salida:
    data/models/vgg16_scene_classifier.pth   ← pesos entrenados
    data/models/training_history.json        ← métricas por época

Requisitos:
    - Haber ejecutado prepare_dataset.py primero
    - torch, torchvision (ya en requirements.txt)
    - ~2-4 GB de RAM
    - Tiempo: ~15-30 min en CPU, ~5 min con GPU
"""
import sys
import json
import time
import copy
from pathlib import Path
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# ── Path raíz del proyecto ────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.config import SCENE_CATEGORIES, DATA_DIR, MODELS_DIR, BATCH_SIZE
from src.processors.scene_processor import VGG16SceneClassifier

# ── Configuración de entrenamiento ────────────────────────────────────────────
DATASET_DIR   = DATA_DIR / 'dataset'
WEIGHTS_PATH  = MODELS_DIR / 'vgg16_scene_classifier.pth'
HISTORY_PATH  = MODELS_DIR / 'training_history.json'

NUM_EPOCHS    = 20       # épocas máximas
LEARNING_RATE = 1e-3     # lr inicial para la cabeza
LR_PATIENCE   = 4        # épocas sin mejora antes de reducir lr
STOP_PATIENCE = 7        # épocas sin mejora antes de parar (early stopping)
TRAIN_BATCH   = min(BATCH_SIZE, 32)
VAL_BATCH     = 32

# Normalización ImageNet (obligatoria para VGG-16)
_MEAN = [0.485, 0.456, 0.406]
_STD  = [0.229, 0.224, 0.225]


def build_transforms() -> Dict[str, transforms.Compose]:
    """
    Pipelines de transformación para train y val.

    Train incluye data augmentation (flip, rotación, color jitter)
    para mejorar generalización con dataset pequeño.
    Val usa solo resize + normalización estándar.
    """
    return {
        'train': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=10),
            transforms.ColorJitter(
                brightness=0.2, contrast=0.2, saturation=0.2
            ),
            transforms.ToTensor(),
            transforms.Normalize(mean=_MEAN, std=_STD),
        ]),
        'val': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=_MEAN, std=_STD),
        ]),
    }


def build_dataloaders(
    tfms: Dict[str, transforms.Compose]
) -> Tuple[Dict[str, DataLoader], Dict[str, int]]:
    """
    Crea DataLoaders de train y val desde data/dataset/.

    Args:
        tfms: Diccionario con transformaciones por split.

    Returns:
        Tupla (dataloaders, tamaños de dataset por split).
    """
    datasets_dict = {
        split: datasets.ImageFolder(
            root=str(DATASET_DIR / split),
            transform=tfms[split],
        )
        for split in ['train', 'val']
    }

    dataloaders = {
        'train': DataLoader(
            datasets_dict['train'],
            batch_size=TRAIN_BATCH,
            shuffle=True,
            num_workers=0,    # 0 = compatible con Windows sin multiprocessing
            pin_memory=torch.cuda.is_available(),
        ),
        'val': DataLoader(
            datasets_dict['val'],
            batch_size=VAL_BATCH,
            shuffle=False,
            num_workers=0,
            pin_memory=torch.cuda.is_available(),
        ),
    }

    sizes = {s: len(datasets_dict[s]) for s in ['train', 'val']}
    return dataloaders, sizes


def verify_class_order(dataloaders: Dict[str, DataLoader]) -> None:
    """
    Verifica que el orden de clases del DataLoader coincida con
    SCENE_CATEGORIES de config.py. Si no coincide, lanza un error
    claro antes de iniciar el entrenamiento.
    """
    detected = dataloaders['train'].dataset.classes
    if detected != SCENE_CATEGORIES:
        print("\n⚠  ADVERTENCIA: El orden de clases detectado no coincide")
        print(f"   Config   : {SCENE_CATEGORIES}")
        print(f"   Dataset  : {detected}")
        print("\n   Asegúrate de que las carpetas en data/dataset/train/")
        print("   tengan exactamente estos nombres (en este orden):")
        for cat in SCENE_CATEGORIES:
            print(f"     - {cat}")
        print("\n   ImageFolder ordena las clases alfabéticamente.")
        print("   Ajusta SCENE_CATEGORIES en config.py para que coincida,")
        print(f"   o renombra las carpetas según: {sorted(SCENE_CATEGORIES)}")
        # No bloqueamos: advertimos y continuamos con el orden detectado


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
) -> Tuple[float, float]:
    """
    Entrena el modelo durante una época.

    Returns:
        (loss_promedio, accuracy) de la época.
    """
    model.train()
    running_loss = 0.0
    correct = 0
    total   = 0

    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * inputs.size(0)
        _, predicted  = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total   += labels.size(0)

    return running_loss / total, correct / total


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> Tuple[float, float]:
    """
    Evalúa el modelo en el conjunto de validación.

    Returns:
        (loss_promedio, accuracy) de validación.
    """
    model.eval()
    running_loss = 0.0
    correct = 0
    total   = 0

    with torch.no_grad():
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss    = criterion(outputs, labels)

            running_loss += loss.item() * inputs.size(0)
            _, predicted  = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total   += labels.size(0)

    return running_loss / total, correct / total


def train(
    model: nn.Module,
    dataloaders: Dict[str, DataLoader],
    sizes: Dict[str, int],
    device: torch.device,
) -> Dict:
    """
    Bucle principal de entrenamiento con:
        - Early stopping (STOP_PATIENCE épocas sin mejora en val_acc)
        - ReduceLROnPlateau (LR_PATIENCE épocas sin mejora)
        - Guardado del mejor modelo

    Args:
        model:       VGG16SceneClassifier con backbone congelado.
        dataloaders: DataLoaders de train y val.
        sizes:       Número de ejemplos por split.
        device:      Dispositivo de cómputo.

    Returns:
        Historial de métricas por época.
    """
    criterion = nn.CrossEntropyLoss()

    # Solo entrenar la cabeza (backbone congelado)
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
        weight_decay=1e-4,
    )

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5,
        patience=LR_PATIENCE, verbose=True,
    )

    history = {
        'train_loss': [], 'train_acc': [],
        'val_loss':   [], 'val_acc':   [],
    }

    best_val_acc   = 0.0
    best_weights   = copy.deepcopy(model.state_dict())
    no_improve     = 0
    start_time     = time.time()

    print(f"\n{'Época':>6} {'Train Loss':>12} {'Train Acc':>10} "
          f"{'Val Loss':>10} {'Val Acc':>9} {'LR':>10}")
    print("-" * 62)

    for epoch in range(1, NUM_EPOCHS + 1):
        t_loss, t_acc = train_one_epoch(
            model, dataloaders['train'], criterion, optimizer, device
        )
        v_loss, v_acc = evaluate(
            model, dataloaders['val'], criterion, device
        )

        scheduler.step(v_acc)
        current_lr = optimizer.param_groups[0]['lr']

        history['train_loss'].append(round(t_loss, 4))
        history['train_acc'].append(round(t_acc,  4))
        history['val_loss'].append(round(v_loss,   4))
        history['val_acc'].append(round(v_acc,     4))

        improved = '  ← mejor' if v_acc > best_val_acc else ''
        print(f"  {epoch:>4}  {t_loss:>11.4f}  {t_acc:>9.1%}  "
              f"{v_loss:>9.4f}  {v_acc:>8.1%}  {current_lr:>9.2e}"
              f"{improved}")

        if v_acc > best_val_acc:
            best_val_acc = v_acc
            best_weights = copy.deepcopy(model.state_dict())
            no_improve   = 0
        else:
            no_improve += 1

        if no_improve >= STOP_PATIENCE:
            print(f"\n  Early stopping en época {epoch} "
                  f"(sin mejora en {STOP_PATIENCE} épocas)")
            break

    elapsed = time.time() - start_time
    print(f"\n  Tiempo total: {elapsed/60:.1f} min")
    print(f"  Mejor val_acc: {best_val_acc:.1%}")

    # Restaurar mejores pesos y guardar
    model.load_state_dict(best_weights)
    torch.save(best_weights, WEIGHTS_PATH)
    print(f"  Pesos guardados en: {WEIGHTS_PATH}")

    history['best_val_acc'] = round(best_val_acc, 4)
    history['epochs_trained'] = epoch
    history['train_seconds'] = round(elapsed, 1)

    HISTORY_PATH.write_text(json.dumps(history, indent=2))
    print(f"  Historial guardado en: {HISTORY_PATH}")

    return history


def print_per_class_accuracy(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    class_names: List[str],
) -> None:
    """Imprime la exactitud por categoría en el conjunto de validación."""
    model.eval()
    correct_per_class = {c: 0 for c in class_names}
    total_per_class   = {c: 0 for c in class_names}

    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            for label, pred in zip(labels, predicted.cpu()):
                cls = class_names[label.item()]
                total_per_class[cls]   += 1
                correct_per_class[cls] += int(label.item() == pred.item())

    print("\nExactitud por categoría (validación):")
    print("-" * 40)
    for cls in class_names:
        t = total_per_class[cls]
        c = correct_per_class[cls]
        acc = c / t if t > 0 else 0
        bar = '█' * int(acc * 20)
        print(f"  {cls:<28} {acc:>6.1%}  {bar}")


# Importación tardía para evitar error de tipo en la anotación
from typing import List


def main() -> None:
    print("=" * 60)
    print("   FINE-TUNING VGG-16 - PTITU")
    print("=" * 60)

    # Verificar dataset
    if not (DATASET_DIR / 'train').exists():
        print("\n✗ Dataset no encontrado.")
        print("  Ejecuta primero: python scripts/prepare_dataset.py")
        sys.exit(1)

    # Dispositivo
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDispositivo : {device}")
    if device.type == 'cpu':
        print("  (Sin GPU — el entrenamiento tomará ~20-40 min)")
    print(f"Épocas máx. : {NUM_EPOCHS}  |  Batch: {TRAIN_BATCH}  |  LR: {LEARNING_RATE}")

    # DataLoaders
    tfms = build_transforms()
    dataloaders, sizes = build_dataloaders(tfms)
    verify_class_order(dataloaders)

    class_names = dataloaders['train'].dataset.classes
    print(f"\nClases detectadas: {class_names}")
    print(f"Train: {sizes['train']} imágenes  |  Val: {sizes['val']} imágenes")

    # Modelo: backbone congelado, solo se entrena la cabeza
    model = VGG16SceneClassifier(
        num_classes=len(SCENE_CATEGORIES),
        freeze_backbone=True,
    ).to(device)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"\nParámetros entrenables: {trainable:,} / {total:,} "
          f"({trainable/total:.1%} del total)")

    # Entrenamiento
    print("\n" + "=" * 60)
    print("INICIANDO ENTRENAMIENTO")
    print("=" * 60)
    history = train(model, dataloaders, sizes, device)

    # Exactitud por clase
    print_per_class_accuracy(model, dataloaders['val'], device, class_names)

    print("\n" + "=" * 60)
    print("✓ ENTRENAMIENTO COMPLETADO")
    print(f"  Mejor val_acc : {history['best_val_acc']:.1%}")
    print(f"  Modelo guardado: {WEIGHTS_PATH}")
    print("\nPara usar el modelo entrenado en SceneProcessor:")
    print(f"  processor = SceneProcessor(weights_path=Path('{WEIGHTS_PATH}'))")
    print("=" * 60)


if __name__ == '__main__':
    main()