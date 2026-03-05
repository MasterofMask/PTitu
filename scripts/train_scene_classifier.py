"""
Fine-tuning profundo de VGG-16 para clasificación de escenas.

Estrategia de dos fases:
    Fase 1 (épocas 1-10): Solo entrena la cabeza de clasificación
                          con LR alto. Backbone completamente congelado.
    Fase 2 (épocas 11+):  Descongela los bloques 4 y 5 de VGG-16
                          con LR muy bajo para ajuste fino.

Arquitectura VGG-16 — capas convolucionales:
    features[0-4]   → Bloque 1 (Conv 64)   ← CONGELADO siempre
    features[5-9]   → Bloque 2 (Conv 128)  ← CONGELADO siempre
    features[10-16] → Bloque 3 (Conv 256)  ← CONGELADO siempre
    features[17-23] → Bloque 4 (Conv 512)  ← se descongela en Fase 2
    features[24-30] → Bloque 5 (Conv 512)  ← se descongela en Fase 2
    classifier      → Cabeza 5 clases      ← siempre entrenable

Uso:
    python scripts/train_scene_classifier.py

Salida:
    data/models/vgg16_scene_classifier.pth
    data/models/training_history.json
"""
import sys
import json
import time
import copy
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.config import SCENE_CATEGORIES, DATA_DIR, MODELS_DIR, BATCH_SIZE
from src.processors.scene_processor import VGG16SceneClassifier

# ── Configuración ─────────────────────────────────────────────────────────────
DATASET_DIR   = DATA_DIR / 'dataset'
WEIGHTS_PATH  = MODELS_DIR / 'vgg16_scene_classifier.pth'
HISTORY_PATH  = MODELS_DIR / 'training_history.json'

# Fase 1: solo cabeza
PHASE1_EPOCHS = 10
PHASE1_LR     = 1e-3

# Fase 2: fine-tuning profundo bloques 4 y 5
PHASE2_EPOCHS = 15
PHASE2_LR_HEAD     = 1e-4   # LR más bajo para la cabeza en fase 2
PHASE2_LR_BACKBONE = 1e-5   # LR muy bajo para las capas descongeladas

STOP_PATIENCE = 7    # early stopping
LR_PATIENCE   = 3    # reducir LR
TRAIN_BATCH   = min(BATCH_SIZE, 32)

# Índices de las capas del backbone que se descongelan en Fase 2
# Bloque 4: features[17..23], Bloque 5: features[24..30]
UNFREEZE_FROM = 17

_MEAN = [0.485, 0.456, 0.406]
_STD  = [0.229, 0.224, 0.225]


def build_transforms() -> Dict[str, transforms.Compose]:
    """Transformaciones con data augmentation para train."""
    return {
        'train': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(
                brightness=0.3, contrast=0.3, saturation=0.2
            ),
            transforms.RandomPerspective(distortion_scale=0.2, p=0.3),
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
) -> Tuple[Dict[str, DataLoader], Dict[str, int], List[str]]:
    """Crea DataLoaders de train y val."""
    ds = {
        split: datasets.ImageFolder(
            root=str(DATASET_DIR / split),
            transform=tfms[split],
        )
        for split in ['train', 'val']
    }
    loaders = {
        'train': DataLoader(ds['train'], batch_size=TRAIN_BATCH,
                            shuffle=True,  num_workers=0,
                            pin_memory=torch.cuda.is_available()),
        'val':   DataLoader(ds['val'],   batch_size=32,
                            shuffle=False, num_workers=0,
                            pin_memory=torch.cuda.is_available()),
    }
    sizes  = {s: len(ds[s]) for s in ['train', 'val']}
    labels = ds['train'].classes
    return loaders, sizes, labels


def unfreeze_blocks_4_5(model: VGG16SceneClassifier) -> None:
    """
    Descongela los bloques 4 y 5 del backbone VGG-16.
    Los bloques 1-3 permanecen congelados para preservar
    características generales de bajo nivel.
    """
    for i, layer in enumerate(model.features):
        if i >= UNFREEZE_FROM:
            for param in layer.parameters():
                param.requires_grad = True


def count_trainable(model: nn.Module) -> Tuple[int, int]:
    total     = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters()
                    if p.requires_grad)
    return trainable, total


def train_one_epoch(
    model: nn.Module, loader: DataLoader,
    criterion: nn.Module, optimizer: optim.Optimizer,
    device: torch.device,
) -> Tuple[float, float]:
    model.train()
    running_loss = correct = total = 0
    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        loss = criterion(model(inputs), labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * inputs.size(0)
        _, pred = model(inputs).detach().max(1)
        correct += pred.eq(labels).sum().item()
        total   += labels.size(0)
    return running_loss / total, correct / total


def evaluate(
    model: nn.Module, loader: DataLoader,
    criterion: nn.Module, device: torch.device,
) -> Tuple[float, float]:
    model.eval()
    running_loss = correct = total = 0
    with torch.no_grad():
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            out  = model(inputs)
            loss = criterion(out, labels)
            running_loss += loss.item() * inputs.size(0)
            _, pred = out.max(1)
            correct += pred.eq(labels).sum().item()
            total   += labels.size(0)
    return running_loss / total, correct / total


def run_phase(
    phase: int,
    model: nn.Module,
    loaders: Dict[str, DataLoader],
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    max_epochs: int,
    history: Dict,
    best_val_acc: float,
    best_weights: Dict,
) -> Tuple[float, Dict, int]:
    """
    Ejecuta una fase de entrenamiento con early stopping.

    Returns:
        (mejor val_acc, mejores pesos, épocas entrenadas)
    """
    scheduler  = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5,
        patience=LR_PATIENCE, verbose=True,
    )
    no_improve = 0

    print(f"\n{'Época':>6} {'Train Loss':>12} {'Train Acc':>10} "
          f"{'Val Loss':>10} {'Val Acc':>9} {'LR':>10}")
    print("-" * 62)

    for epoch in range(1, max_epochs + 1):
        t_loss, t_acc = train_one_epoch(
            model, loaders['train'], criterion, optimizer, device
        )
        v_loss, v_acc = evaluate(
            model, loaders['val'], criterion, device
        )
        scheduler.step(v_acc)
        lr = optimizer.param_groups[0]['lr']

        history['train_loss'].append(round(t_loss, 4))
        history['train_acc'].append(round(t_acc,   4))
        history['val_loss'].append(round(v_loss,   4))
        history['val_acc'].append(round(v_acc,     4))

        tag = '  ← mejor' if v_acc > best_val_acc else ''
        print(f"  {epoch:>4}  {t_loss:>11.4f}  {t_acc:>9.1%}  "
              f"{v_loss:>9.4f}  {v_acc:>8.1%}  {lr:>9.2e}{tag}")

        if v_acc > best_val_acc:
            best_val_acc = v_acc
            best_weights = copy.deepcopy(model.state_dict())
            no_improve   = 0
        else:
            no_improve  += 1

        if no_improve >= STOP_PATIENCE:
            print(f"\n  Early stopping (fase {phase}, época {epoch})")
            break

    return best_val_acc, best_weights, epoch


def per_class_accuracy(
    model: nn.Module, loader: DataLoader,
    device: torch.device, class_names: List[str],
) -> None:
    model.eval()
    correct = {c: 0 for c in class_names}
    total   = {c: 0 for c in class_names}
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            _, pred = model(inputs).max(1)
            for lbl, p in zip(labels, pred.cpu()):
                cls = class_names[lbl.item()]
                total[cls]   += 1
                correct[cls] += int(lbl.item() == p.item())
    print("\nExactitud por categoría (validación):")
    print("-" * 45)
    for cls in class_names:
        t   = total[cls]
        acc = correct[cls] / t if t > 0 else 0
        bar = '█' * int(acc * 20)
        print(f"  {cls:<28} {acc:>6.1%}  {bar}")


def main() -> None:
    print("=" * 60)
    print("   FINE-TUNING VGG-16 (2 FASES) - PTITU")
    print("=" * 60)

    if not (DATASET_DIR / 'train').exists():
        print("\n✗ Dataset no encontrado.")
        print("  Ejecuta: python scripts/prepare_dataset.py")
        sys.exit(1)

    try:
        import torch_directml
        device = torch_directml.device()
        print(f"Dispositivo : AMD GPU (DirectML)")
    except ImportError:
        device = torch.device('cpu')
        print(f"Dispositivo : cpu")
        print(f"\nDispositivo : {device}")

    if device.type == 'cpu':
        print("  (Sin GPU — ~40-70 min total para 2 fases)")

    tfms = build_transforms()
    loaders, sizes, class_names = build_dataloaders(tfms)

    if class_names != SCENE_CATEGORIES:
        print(f"\n⚠  Orden detectado : {class_names}")
        print(f"   Actualizando config internamente para este entrenamiento")

    print(f"\nClases  : {class_names}")
    print(f"Train   : {sizes['train']} imágenes")
    print(f"Val     : {sizes['val']} imágenes")

    model     = VGG16SceneClassifier(
        num_classes=len(SCENE_CATEGORIES), freeze_backbone=True
    ).to(device)
    criterion = nn.CrossEntropyLoss()

    history = {
        'train_loss': [], 'train_acc': [],
        'val_loss':   [], 'val_acc':   [],
        'phase_boundary': None,
    }
    best_val_acc = 0.0
    best_weights = copy.deepcopy(model.state_dict())
    start_time   = time.time()

    # ── FASE 1: Solo cabeza ───────────────────────────────────────────────────
    trainable, total = count_trainable(model)
    print(f"\n{'─'*60}")
    print(f"FASE 1 — Entrenamiento de cabeza ({PHASE1_EPOCHS} épocas máx.)")
    print(f"  Parámetros entrenables: {trainable:,} / {total:,} "
          f"({trainable/total:.1%})")
    print(f"{'─'*60}")

    optimizer1 = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=PHASE1_LR, weight_decay=1e-4,
    )
    best_val_acc, best_weights, ep1 = run_phase(
        1, model, loaders, optimizer1, criterion,
        device, PHASE1_EPOCHS, history, best_val_acc, best_weights
    )
    history['phase_boundary'] = len(history['val_acc'])
    print(f"\n  Fase 1 completada — mejor val_acc: {best_val_acc:.1%}")

    # ── FASE 2: Descongelar bloques 4 y 5 ────────────────────────────────────
    model.load_state_dict(best_weights)  # partir del mejor punto de fase 1
    unfreeze_blocks_4_5(model)

    trainable2, _ = count_trainable(model)
    print(f"\n{'─'*60}")
    print(f"FASE 2 — Fine-tuning bloques 4+5 ({PHASE2_EPOCHS} épocas máx.)")
    print(f"  Parámetros entrenables: {trainable2:,} / {total:,} "
          f"({trainable2/total:.1%})")
    print(f"  LR cabeza: {PHASE2_LR_HEAD:.0e}  |  "
          f"LR backbone: {PHASE2_LR_BACKBONE:.0e}")
    print(f"{'─'*60}")

    # Dos grupos de parámetros con LR diferente
    backbone_params = [
        p for i, layer in enumerate(model.features)
        if i >= UNFREEZE_FROM
        for p in layer.parameters()
        if p.requires_grad
    ]
    head_params = list(model.classifier.parameters())

    optimizer2 = optim.Adam([
        {'params': backbone_params, 'lr': PHASE2_LR_BACKBONE},
        {'params': head_params,     'lr': PHASE2_LR_HEAD},
    ], weight_decay=1e-4)

    best_val_acc, best_weights, ep2 = run_phase(
        2, model, loaders, optimizer2, criterion,
        device, PHASE2_EPOCHS, history, best_val_acc, best_weights
    )

    # ── Guardar modelo ────────────────────────────────────────────────────────
    model.load_state_dict(best_weights)
    torch.save(best_weights, WEIGHTS_PATH)

    elapsed = time.time() - start_time
    history['best_val_acc']   = round(best_val_acc, 4)
    history['epochs_phase1']  = ep1
    history['epochs_phase2']  = ep2
    history['train_seconds']  = round(elapsed, 1)
    HISTORY_PATH.write_text(json.dumps(history, indent=2))

    # ── Resultados finales ────────────────────────────────────────────────────
    per_class_accuracy(model, loaders['val'], device, class_names)

    print(f"\n  Tiempo total : {elapsed/60:.1f} min")
    print(f"  Mejor val_acc: {best_val_acc:.1%}")

    print("\n" + "=" * 60)
    print("✓ ENTRENAMIENTO COMPLETADO")
    print(f"  Modelo guardado: {WEIGHTS_PATH}")
    print("\nPara usar el modelo:")
    print(f"  processor = SceneProcessor("
          f"weights_path=MODELS_DIR / 'vgg16_scene_classifier.pth')")
    print("=" * 60)


if __name__ == '__main__':
    main()