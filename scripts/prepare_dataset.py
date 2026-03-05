"""
Preparación de dataset usando AI-Challenger-Scene-Classification.

Mapea las 80 categorías del dataset a las 5 categorías del proyecto:
    - interiores
    - exteriores
    - restaurantes
    - eventos_sociales
    - actividades_deportivas

Uso:
    python scripts/prepare_dataset.py
"""
import sys
import json
import shutil
import random
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.config import SCENE_CATEGORIES, DATA_DIR

# ── Configuración ─────────────────────────────────────────────────────────────
DATASET_DIR    = DATA_DIR / 'dataset'
TRAIN_DIR      = DATASET_DIR / 'train'
VAL_DIR        = DATASET_DIR / 'val'
IMAGES_PER_CAT = 1000  # imágenes por categoría (160 train + 40 val)
VAL_SPLIT      = 0.20
SEED           = 42

# ── Mapeo: label_id del dataset → categoría del proyecto ─────────────────────
# Basado en las 80 clases del AI-Challenger Scene Classification
LABEL_MAPPING: Dict[int, str] = {

    # ── interiores ────────────────────────────────────────────────────────────
    2:  'interiores',   # airplane_cabin
    6:  'interiores',   # art_room
    35: 'interiores',   # kitchen
    37: 'interiores',   # laboratory
    40: 'interiores',   # office
    41: 'interiores',   # hospital
    44: 'interiores',   # music_studio
    51: 'interiores',   # library/bookstore
    52: 'interiores',   # classroom
    57: 'interiores',   # balcony
    58: 'interiores',   # recreation_room
    60: 'interiores',   # museum
    68: 'interiores',   # aquarium
    71: 'interiores',   # bedchamber
    75: 'interiores',   # nursery
    26: 'interiores',   # television_studio

    # ── exteriores ────────────────────────────────────────────────────────────
    0:  'exteriores',   # airport_terminal
    1:  'exteriores',   # landing_field
    29: 'exteriores',   # tower
    30: 'exteriores',   # palace
    32: 'exteriores',   # street
    36: 'exteriores',   # plaza
    42: 'exteriores',   # ticket_booth
    43: 'exteriores',   # campsite
    45: 'exteriores',   # elevator/staircase
    46: 'exteriores',   # garden
    47: 'exteriores',   # construction_site
    55: 'exteriores',   # gas_station
    64: 'exteriores',   # bridge
    65: 'exteriores',   # residential_neighborhood
    73: 'exteriores',   # station/platform
    28: 'exteriores',   # pavilion
    53: 'exteriores',  # ocean/beach (reuniones)
    74: 'exteriores',  # lawn (reuniones al aire libre)
    62: 'exteriores',  # raft

    # ── restaurantes ─────────────────────────────────────────────────────────
    33: 'restaurantes', # dining_room
    34: 'restaurantes', # coffee_shop
    38: 'restaurantes', # bar
    48: 'restaurantes', # general_store
    49: 'restaurantes', # clothing_store
    50: 'restaurantes', # bazaar
    66: 'restaurantes', # auto_showroom
    76: 'restaurantes', # beauty_salon
    77: 'restaurantes', # repair_shop


    # ── eventos_sociales ──────────────────────────────────────────────────────
    3:  'eventos_sociales',  # amusement_park
    5:  'eventos_sociales',  # arena/performance
    25: 'eventos_sociales',  # greenhouse (exposiciones)
    56: 'eventos_sociales',  # landfill — se excluye abajo
    59: 'eventos_sociales', # discotheque
    27: 'eventos_sociales',   # temple/east_asia (reuniones religiosas)
    31: 'eventos_sociales',   # church (misas, bodas)
    39: 'eventos_sociales',   # conference_room 
    70: 'eventos_sociales',   # banquet_hall 

    
    

    # ── actividades_deportivas ────────────────────────────────────────────────
    4:  'actividades_deportivas',  # skating_rink
    8:  'actividades_deportivas',  # baseball_field
    9:  'actividades_deportivas',  # football_field
    10: 'actividades_deportivas',  # soccer_field
    11: 'actividades_deportivas',  # volleyball_court
    12: 'actividades_deportivas',  # golf_course
    13: 'actividades_deportivas',  # athletic_field
    14: 'actividades_deportivas',  # ski_slope
    15: 'actividades_deportivas',  # basketball_court
    16: 'actividades_deportivas',  # gymnasium
    17: 'actividades_deportivas',  # bowling_alley
    18: 'actividades_deportivas',  # swimming_pool
    19: 'actividades_deportivas',  # boxing_ring
    20: 'actividades_deportivas',  # racecourse
    78: 'actividades_deportivas',  # rodeo
}

# Excluir estas label_ids (categorías poco representativas o ambiguas)
EXCLUDE_LABELS = {56, 62}  # landfill, raft


def create_dirs() -> None:
    print("Creando carpetas...")
    for split in [TRAIN_DIR, VAL_DIR]:
        for cat in SCENE_CATEGORIES:
            (split / cat).mkdir(parents=True, exist_ok=True)
    print(f"  ✓ {DATASET_DIR}\n")


def load_annotations(json_path: Path) -> Dict[str, str]:
    """
    Carga el JSON de anotaciones y retorna {image_id: label_id}.

    Args:
        json_path: Ruta al archivo JSON de anotaciones.

    Returns:
        Diccionario imagen_id → label_id (string).
    """
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    return {item['image_id']: item['label_id'] for item in data}


def build_category_index(
    annotations: Dict[str, str],
    images_dir: Path,
) -> Dict[str, List[Path]]:
    """
    Construye un índice {categoria: [rutas de imagen]} filtrando
    solo las imágenes que existen en disco y tienen categoría mapeada.

    Args:
        annotations: Diccionario {image_id: label_id}.
        images_dir:  Directorio donde están las imágenes.

    Returns:
        Diccionario {categoria: lista de rutas}.
    """
    index: Dict[str, List[Path]] = {cat: [] for cat in SCENE_CATEGORIES}

    for image_id, label_str in annotations.items():
        label_id = int(label_str)

        if label_id in EXCLUDE_LABELS:
            continue

        category = LABEL_MAPPING.get(label_id)
        if category is None:
            continue

        img_path = images_dir / image_id
        if img_path.exists():
            index[category].append(img_path)

    return index


def copy_images(sources: List[Path], dest_dir: Path,
                prefix: str, start_idx: int = 0) -> int:
    """Copia imágenes al directorio destino con nombre secuencial."""
    copied = 0
    for i, src in enumerate(sources):
        dest = dest_dir / f"{prefix}_{start_idx + i:04d}{src.suffix.lower()}"
        try:
            shutil.copy2(src, dest)
            copied += 1
        except Exception as e:
            print(f"    ⚠ {src.name}: {e}")
    return copied


def split_val(cat: str) -> None:
    """Mueve el 20% de imágenes de train a val."""
    imgs = list((TRAIN_DIR / cat).glob('*.*'))
    random.shuffle(imgs)
    n_val = max(1, int(len(imgs) * VAL_SPLIT))
    for p in imgs[:n_val]:
        shutil.move(str(p), str(VAL_DIR / cat / p.name))


def print_summary() -> None:
    print(f"\n  {'Categoría':<28} {'Train':>7} {'Val':>7} {'Total':>7}")
    print("  " + "─" * 50)
    total_t = total_v = 0
    for cat in SCENE_CATEGORIES:
        t = len(list((TRAIN_DIR / cat).glob('*.*')))
        v = len(list((VAL_DIR   / cat).glob('*.*')))
        total_t += t
        total_v += v
        estado = "✓" if t >= 100 else "⚠ pocas"
        print(f"  {cat:<28} {t:>7} {v:>7} {t+v:>7}  {estado}")
    print("  " + "─" * 50)
    print(f"  {'TOTAL':<28} {total_t:>7} {total_v:>7} {total_t+total_v:>7}")


def main() -> None:
    random.seed(SEED)

    import kagglehub
    dataset_path = Path(kagglehub.dataset_download(
        'kjeanclaude/ai-challenger-scene-classification'
    ))

    print("=" * 60)
    print("   PREPARACIÓN DE DATASET - PTITU")
    print("   Fuente: AI-Challenger Scene Classification (Kaggle)")
    print("=" * 60)
    print(f"\nCategorías  : {', '.join(SCENE_CATEGORIES)}")
    print(f"Por categoría: ~{int(IMAGES_PER_CAT*0.8)} train + "
          f"~{int(IMAGES_PER_CAT*0.2)} val")
    print(f"Clases mapeadas: {len(LABEL_MAPPING)} de 80 disponibles\n")

    create_dirs()

    # ── Procesar split de entrenamiento ───────────────────────────────────────
    train_json = (dataset_path /
                  'aichallengerTrain/ai_challenger_scene_train_20170904'
                  '/scene_train_annotations_20170904.json')
    train_imgs = (dataset_path /
                  'aichallengerTrain/ai_challenger_scene_train_20170904'
                  '/scene_train_images_20170904')

    print("Indexando anotaciones de train (~54k imágenes)...", end='', flush=True)
    train_ann = load_annotations(train_json)
    train_idx = build_category_index(train_ann, train_imgs)
    print(f" ✓  ({len(train_ann):,} anotaciones)\n")

    print("Copiando imágenes por categoría:")
    for cat in SCENE_CATEGORIES:
        available = train_idx[cat]
        random.shuffle(available)
        selected  = available[:IMAGES_PER_CAT]
        n = copy_images(selected, TRAIN_DIR / cat, prefix=cat)
        print(f"  {cat:<28} {n:>5} imágenes  "
              f"(disponibles: {len(available):,})")

    # ── Procesar validación del dataset para completar si faltan ──────────────
    val_json = (dataset_path /
                'ai_challenger_scene_validation_20170908'
                '/ai_challenger_scene_validation_20170908'
                '/scene_validation_annotations_20170908.json')
    val_imgs = (dataset_path /
                'ai_challenger_scene_validation_20170908'
                '/ai_challenger_scene_validation_20170908'
                '/scene_validation_images_20170908')

    print("\nIndexando validación del dataset...", end='', flush=True)
    val_ann = load_annotations(val_json)
    val_idx = build_category_index(val_ann, val_imgs)
    print(f" ✓  ({len(val_ann):,} anotaciones)\n")

    # Completar categorías con pocas imágenes usando el split de validación
    print("Completando categorías con pocas imágenes...")
    for cat in SCENE_CATEGORIES:
        current = len(list((TRAIN_DIR / cat).glob('*.*')))
        if current < IMAGES_PER_CAT:
            needed    = IMAGES_PER_CAT - current
            available = val_idx[cat]
            random.shuffle(available)
            selected  = available[:needed]
            n = copy_images(selected, TRAIN_DIR / cat,
                            prefix=cat, start_idx=current)
            if n > 0:
                print(f"  {cat:<28} +{n} imágenes adicionales")

    # ── Dividir train/val ─────────────────────────────────────────────────────
    print("\nDividiendo train / val (80/20)...")
    for cat in SCENE_CATEGORIES:
        split_val(cat)
        t = len(list((TRAIN_DIR / cat).glob('*.*')))
        v = len(list((VAL_DIR   / cat).glob('*.*')))
        print(f"  ✓ {cat:<28} train={t}  val={v}")

    # ── Resumen ───────────────────────────────────────────────────────────────
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