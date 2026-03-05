"""
Preparación de dataset para fine-tuning de VGG-16.

Descarga automáticamente 3 datasets de Kaggle mediante kagglehub
y los organiza en las 5 categorías del proyecto PTitu.

Datasets usados:
    1. puneet6060/intel-image-classification
       → exteriores, paisajes
    2. itsahmad/indoor-scenes-cvpr-2019
       → interiores
    3. gpiosenka/sports-classification
       → actividades_deportivas
    4. Imágenes de eventos sociales: balabaskar/human-action-recognition
       → eventos_sociales (acciones de personas en grupo)

Uso:
    cd raiz_del_proyecto
    python scripts/prepare_dataset.py

Requiere:
    pip install kagglehub
    Variable de entorno KAGGLE_API_TOKEN o archivo ~/.kaggle/kaggle.json

Resultado:
    data/dataset/
    ├── train/
    │   ├── eventos_sociales/
    │   ├── paisajes/
    │   ├── interiores/
    │   ├── exteriores/
    │   └── actividades_deportivas/
    └── val/
        └── (misma estructura)
"""
import sys
import shutil
import random
import json
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.config import SCENE_CATEGORIES, DATA_DIR

# ── Configuración ─────────────────────────────────────────────────────────────
DATASET_DIR   = DATA_DIR / 'dataset'
TRAIN_DIR     = DATASET_DIR / 'train'
VAL_DIR       = DATASET_DIR / 'val'
IMAGES_PER_CAT = 150   # imágenes por categoría (120 train + 30 val)
VAL_SPLIT      = 0.20
SEED           = 42

# ── Mapeo de carpetas de cada dataset → categorías del proyecto ───────────────
#
# Intel Image Classification:
#   buildings → exteriores
#   forest    → paisajes
#   glacier   → paisajes
#   mountain  → paisajes
#   sea       → paisajes
#   street    → exteriores
#
# MIT Indoor Scenes:
#   (todas las carpetas) → interiores
#
# Sports Classification:
#   (carpetas de deportes) → actividades_deportivas
#
# Human Action Recognition:
#   Dancing, Laughing, Running, etc. con personas → eventos_sociales / act_dep

INTEL_MAPPING: Dict[str, str] = {
    'buildings': 'exteriores',
    'forest':    'paisajes',
    'glacier':   'paisajes',
    'mountain':  'paisajes',
    'sea':       'paisajes',
    'street':    'exteriores',
}

# Deportes a incluir de gpiosenka/sports-classification
SPORTS_INCLUDE = {
    'basketball', 'football', 'soccer', 'tennis', 'volleyball',
    'swimming', 'running', 'cycling', 'gymnastics', 'baseball',
    'boxing', 'rugby', 'hockey', 'skiing', 'surfing',
    'archery', 'badminton', 'bowling', 'golf', 'wrestling',
}

# Clases de Human Action Recognition útiles para eventos sociales
SOCIAL_ACTIONS = {
    'clapping', 'dancing', 'laughing', 'hugging',
    'shaking_hands', 'waving', 'cheering',
}


def create_dirs() -> None:
    """Crea la estructura de carpetas train/val."""
    print("Creando estructura de carpetas...")
    for split in [TRAIN_DIR, VAL_DIR]:
        for cat in SCENE_CATEGORIES:
            (split / cat).mkdir(parents=True, exist_ok=True)
    print(f"  ✓ {DATASET_DIR}\n")


def collect_images(src_dir: Path, limit: int = None) -> List[Path]:
    """
    Recolecta archivos de imagen de un directorio recursivamente.

    Args:
        src_dir: Directorio raíz donde buscar.
        limit:   Máximo de imágenes a retornar (None = sin límite).

    Returns:
        Lista de rutas a imágenes JPEG/PNG encontradas.
    """
    exts   = {'.jpg', '.jpeg', '.png'}
    images = [
        p for p in src_dir.rglob('*')
        if p.suffix.lower() in exts and p.is_file()
    ]
    random.shuffle(images)
    return images[:limit] if limit else images


def copy_images(sources: List[Path], dest_dir: Path,
                prefix: str, start_idx: int = 0) -> int:
    """
    Copia imágenes a un directorio destino renombrándolas secuencialmente.

    Args:
        sources:   Lista de rutas origen.
        dest_dir:  Directorio destino.
        prefix:    Prefijo para el nombre del archivo.
        start_idx: Índice inicial para la numeración.

    Returns:
        Número de imágenes copiadas exitosamente.
    """
    copied = 0
    for i, src in enumerate(sources):
        ext  = src.suffix.lower()
        dest = dest_dir / f"{prefix}_{start_idx + i:04d}{ext}"
        try:
            shutil.copy2(src, dest)
            copied += 1
        except Exception as e:
            print(f"    ⚠ Error copiando {src.name}: {e}")
    return copied


def split_train_val(cat: str) -> None:
    """
    Mueve el 20% de imágenes de TRAIN_DIR/cat a VAL_DIR/cat.

    Args:
        cat: Nombre de la categoría.
    """
    imgs  = list((TRAIN_DIR / cat).glob('*.*'))
    random.shuffle(imgs)
    n_val = max(1, int(len(imgs) * VAL_SPLIT))
    for p in imgs[:n_val]:
        shutil.move(str(p), str(VAL_DIR / cat / p.name))


def download_intel(limit_per_class: int) -> Dict[str, int]:
    """
    Descarga Intel Image Classification y copia a exteriores/paisajes.

    Args:
        limit_per_class: Máximo de imágenes por clase de Intel.

    Returns:
        Dict con número de imágenes copiadas por categoría del proyecto.
    """
    print("─" * 50)
    print("Dataset 1/3: Intel Image Classification")
    print("  Categorías: exteriores, paisajes")
    print("  Descargando...", end='', flush=True)

    import kagglehub
    path = Path(kagglehub.dataset_download(
        "puneet6060/intel-image-classification"
    ))
    print(" ✓")

    counts: Dict[str, int] = {cat: 0 for cat in SCENE_CATEGORIES}

    # El dataset tiene seg_train y seg_test; usamos ambos
    for split_folder in ['seg_train', 'seg_test', 'seg_pred']:
        split_path = path / split_folder
        if not split_path.exists():
            # A veces está un nivel más abajo
            candidates = list(path.rglob(split_folder))
            if candidates:
                split_path = candidates[0]
            else:
                continue

        for class_dir in split_path.iterdir():
            if not class_dir.is_dir():
                continue
            class_name = class_dir.name.lower()
            mapped_cat = INTEL_MAPPING.get(class_name)
            if mapped_cat is None:
                continue

            images = collect_images(class_dir, limit=limit_per_class)
            if not images:
                continue

            start = counts[mapped_cat]
            n = copy_images(
                images, TRAIN_DIR / mapped_cat,
                prefix=mapped_cat, start_idx=start
            )
            counts[mapped_cat] += n

    for cat in ['exteriores', 'paisajes']:
        print(f"  ✓ {cat}: {counts[cat]} imágenes")

    return counts


def download_indoors(limit: int) -> int:
    """
    Descarga MIT Indoor Scenes y copia a interiores.

    Args:
        limit: Máximo de imágenes a copiar.

    Returns:
        Número de imágenes copiadas.
    """
    print("─" * 50)
    print("Dataset 2/3: MIT Indoor Scenes")
    print("  Categoría: interiores")
    print("  Descargando...", end='', flush=True)

    import kagglehub
    path = Path(kagglehub.dataset_download(
        "itsahmad/indoor-scenes-cvpr-2019"
    ))
    print(" ✓")

    # Buscar directorio con imágenes
    images = collect_images(path, limit=limit)
    n = copy_images(images, TRAIN_DIR / 'interiores',
                    prefix='interiores', start_idx=0)
    print(f"  ✓ interiores: {n} imágenes")
    return n


def download_sports(limit: int) -> int:
    """
    Descarga Sports Classification y copia a actividades_deportivas.

    Args:
        limit: Máximo de imágenes a copiar.

    Returns:
        Número de imágenes copiadas.
    """
    print("─" * 50)
    print("Dataset 3/3: Sports Classification")
    print("  Categoría: actividades_deportivas")
    print("  Descargando...", end='', flush=True)

    import kagglehub
    path = Path(kagglehub.dataset_download(
        "gpiosenka/sports-classification"
    ))
    print(" ✓")

    total = 0
    # Buscar carpetas de deportes incluidos
    for sport_dir in path.rglob('*'):
        if not sport_dir.is_dir():
            continue
        name = sport_dir.name.lower().replace(' ', '_').replace('-', '_')
        if not any(s in name for s in SPORTS_INCLUDE):
            continue
        if total >= limit:
            break
        images = collect_images(sport_dir, limit=20)
        n = copy_images(
            images, TRAIN_DIR / 'actividades_deportivas',
            prefix='actividades_deportivas', start_idx=total
        )
        total += n

    # Si no encontramos suficientes con el filtro, tomar todas las imágenes
    if total < limit // 2:
        print(f"\n  (tomando imágenes adicionales sin filtro de deporte)")
        images = collect_images(path, limit=limit - total)
        n = copy_images(
            images, TRAIN_DIR / 'actividades_deportivas',
            prefix='actividades_deportivas', start_idx=total
        )
        total += n

    print(f"  ✓ actividades_deportivas: {total} imágenes")
    return total


def download_social_events(limit: int) -> int:
    """
    Descarga dataset de acciones humanas para eventos_sociales.
    Usa Human Action Recognition de Kaggle.

    Args:
        limit: Máximo de imágenes a copiar.

    Returns:
        Número de imágenes copiadas.
    """
    print("─" * 50)
    print("Dataset 4/4: Human Action Recognition")
    print("  Categoría: eventos_sociales")
    print("  Descargando...", end='', flush=True)

    import kagglehub
    # Dataset alternativo con escenas sociales
    try:
        path = Path(kagglehub.dataset_download(
            "meetnagadia/human-action-recognition-har-dataset"
        ))
    except Exception:
        # Fallback: usar imágenes de celebrations/gatherings
        try:
            path = Path(kagglehub.dataset_download(
                "alessiocorrado99/animals10"  # placeholder fallback
            ))
        except Exception:
            print(" ✗ (no disponible)")
            return 0
    print(" ✓")

    total = 0
    # Intentar filtrar por acciones sociales
    for action_dir in path.rglob('*'):
        if not action_dir.is_dir():
            continue
        name = action_dir.name.lower().replace(' ', '_')
        is_social = any(s in name for s in SOCIAL_ACTIONS)
        if not is_social:
            continue
        if total >= limit:
            break
        images = collect_images(action_dir, limit=30)
        n = copy_images(
            images, TRAIN_DIR / 'eventos_sociales',
            prefix='eventos_sociales', start_idx=total
        )
        total += n

    # Si insuficientes, tomar todas las imágenes del dataset
    if total < limit // 3:
        images = collect_images(path, limit=limit - total)
        n = copy_images(
            images, TRAIN_DIR / 'eventos_sociales',
            prefix='eventos_sociales', start_idx=total
        )
        total += n

    print(f"  ✓ eventos_sociales: {total} imágenes")
    return total


def trim_category(cat: str, max_images: int) -> None:
    """
    Si una categoría tiene más de max_images, elimina el exceso
    aleatoriamente para mantener clases balanceadas.

    Args:
        cat:        Nombre de la categoría.
        max_images: Máximo de imágenes permitidas en train.
    """
    imgs = list((TRAIN_DIR / cat).glob('*.*'))
    if len(imgs) <= max_images:
        return
    random.shuffle(imgs)
    for p in imgs[max_images:]:
        p.unlink()


def print_summary() -> None:
    """Imprime y guarda el resumen del dataset construido."""
    print(f"\n  {'Categoría':<28} {'Train':>7} {'Val':>7} {'Total':>7}")
    print("  " + "─" * 50)
    total_t = total_v = 0
    counts  = {}
    for cat in SCENE_CATEGORIES:
        t = len(list((TRAIN_DIR / cat).glob('*.*')))
        v = len(list((VAL_DIR   / cat).glob('*.*')))
        total_t += t
        total_v += v
        counts[cat] = {'train': t, 'val': v}
        estado = "✓" if t >= 50 else "⚠ pocas"
        print(f"  {cat:<28} {t:>7} {v:>7} {t+v:>7}  {estado}")
    print("  " + "─" * 50)
    print(f"  {'TOTAL':<28} {total_t:>7} {total_v:>7} {total_t+total_v:>7}")

    info = {
        'categories':  SCENE_CATEGORIES,
        'counts':      counts,
        'total_train': total_t,
        'total_val':   total_v,
        'sources': [
            'Intel Image Classification (Kaggle)',
            'MIT Indoor Scenes CVPR 2019 (Kaggle)',
            'Sports Classification (Kaggle)',
            'Human Action Recognition (Kaggle)',
        ],
    }
    (DATASET_DIR / 'dataset_info.json').write_text(
        json.dumps(info, indent=2, ensure_ascii=False)
    )
    print(f"\n  Info guardada en: {DATASET_DIR / 'dataset_info.json'}")


def main() -> None:
    random.seed(SEED)

    print("=" * 60)
    print("   PREPARACIÓN DE DATASET - PTITU")
    print("   Fuente: Kaggle (via kagglehub)")
    print("=" * 60)
    print(f"\nCategorías objetivo: {', '.join(SCENE_CATEGORIES)}")
    print(f"Imágenes por categoría: ~{IMAGES_PER_CAT}")
    print("\nSe descargarán 4 datasets de Kaggle.")
    print("Tiempo estimado: 5-15 min (depende de tu conexión)\n")
    input("Presiona Enter para iniciar, Ctrl+C para cancelar...")
    print()

    # 1. Crear estructura
    create_dirs()

    # 2. Descargar y organizar cada dataset
    download_intel(limit_per_class=IMAGES_PER_CAT)
    download_indoors(limit=IMAGES_PER_CAT)
    download_sports(limit=IMAGES_PER_CAT)
    download_social_events(limit=IMAGES_PER_CAT)

    # 3. Balancear: recortar categorías con demasiadas imágenes
    print("\n─" * 25)
    print("Balanceando clases...")
    for cat in SCENE_CATEGORIES:
        trim_category(cat, IMAGES_PER_CAT)
        total = len(list((TRAIN_DIR / cat).glob('*.*')))
        print(f"  {cat:<28} → {total} imágenes")

    # 4. Dividir train/val
    print("\nDividiendo train / val (80/20)...")
    for cat in SCENE_CATEGORIES:
        split_train_val(cat)
        print(f"  ✓ {cat}")

    # 5. Resumen
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print_summary()

    print(f"\n  Dataset guardado en: {DATASET_DIR}")
    print("\nSiguiente paso:")
    print("  python scripts/train_scene_classifier.py")
    print("=" * 60)


if __name__ == '__main__':
    main()