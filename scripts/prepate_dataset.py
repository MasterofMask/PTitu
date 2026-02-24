"""
Preparación de dataset para fine-tuning de VGG-16.

Descarga imágenes gratuitas desde Unsplash Source API (sin clave,
sin registro) y las organiza en las 5 categorías del proyecto.

Categorías objetivo (config.py → SCENE_CATEGORIES):
    - interiores
    - exteriores
    - paisajes
    - eventos_sociales
    - actividades_deportivas

Uso:
    cd raiz_del_proyecto
    python scripts/prepare_dataset.py

Resultado:
    data/dataset/
    ├── train/
    │   ├── interiores/            (~120 imágenes)
    │   ├── exteriores/            (~120 imágenes)
    │   ├── paisajes/              (~120 imágenes)
    │   ├── eventos_sociales/      (~120 imágenes)
    │   └── actividades_deportivas/(~120 imágenes)
    └── val/
        ├── interiores/            (~30 imágenes)
        ├── exteriores/            (~30 imágenes)
        ├── paisajes/              (~30 imágenes)
        ├── eventos_sociales/      (~30 imágenes)
        └── actividades_deportivas/(~30 imágenes)
"""
import sys
import json
import shutil
import random
import urllib.request
from pathlib import Path
from typing import List, Dict

# ── Path raíz del proyecto ────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.config import SCENE_CATEGORIES, DATA_DIR

# ── Configuración ─────────────────────────────────────────────────────────────
DATASET_DIR  = DATA_DIR / 'dataset'
TRAIN_DIR    = DATASET_DIR / 'train'
VAL_DIR      = DATASET_DIR / 'val'
TOTAL_PER_CAT = 150    # descarga total; 80% train, 20% val
VAL_SPLIT     = 0.20
IMG_WIDTH     = 800    # satisface RNF-03 (≥ 640×480)
IMG_HEIGHT    = 600

# ── Keywords por categoría → Unsplash Source ──────────────────────────────────
KEYWORDS: Dict[str, List[str]] = {
    'interiores': [
        'living+room', 'bedroom', 'kitchen+interior', 'office+room',
        'dining+room', 'home+interior', 'cozy+room', 'apartment+interior',
        'indoor+furniture', 'bathroom+interior',
    ],
    'exteriores': [
        'city+street', 'urban+building', 'town+square', 'neighborhood',
        'building+facade', 'outdoor+walkway', 'city+architecture',
        'suburban+house', 'market+outdoor', 'plaza+outdoor',
    ],
    'paisajes': [
        'mountain+landscape', 'beach+nature', 'forest+trees',
        'lake+reflection', 'countryside+field', 'ocean+sunset',
        'valley+landscape', 'waterfall', 'desert+landscape', 'sunrise+nature',
    ],
    'eventos_sociales': [
        'birthday+party', 'wedding+celebration', 'graduation',
        'family+gathering', 'friends+party', 'concert+crowd',
        'festival+people', 'dinner+party', 'social+gathering', 'reunion',
    ],
    'actividades_deportivas': [
        'football+sport', 'basketball+game', 'running+athlete',
        'swimming+competition', 'tennis+match', 'cycling+race',
        'gym+workout', 'soccer+field', 'volleyball+sport', 'sports+action',
    ],
}


def create_dirs() -> None:
    print("Creando carpetas...")
    for split in [TRAIN_DIR, VAL_DIR]:
        for cat in SCENE_CATEGORIES:
            (split / cat).mkdir(parents=True, exist_ok=True)
    print(f"  ✓ {DATASET_DIR}\n")


def download_image(url: str, dest: Path) -> bool:
    """Descarga una imagen. Retorna True si tuvo éxito y el archivo es válido."""
    try:
        req = urllib.request.Request(
            url, headers={'User-Agent': 'PTitu-DatasetCollector/1.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 10_000:   # menor a 10KB = imagen inválida
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        if dest.exists():
            dest.unlink()
        return False


def download_category(cat: str, total: int) -> int:
    """Descarga `total` imágenes de una categoría en TRAIN_DIR/cat/."""
    save_dir  = TRAIN_DIR / cat
    keywords  = KEYWORDS[cat]
    done      = 0
    attempts  = 0
    max_try   = total * 4

    print(f"  {cat:<28}", end='', flush=True)

    while done < total and attempts < max_try:
        kw  = keywords[attempts % len(keywords)]
        sig = attempts * 7 + random.randint(0, 999)
        url = f"https://source.unsplash.com/{IMG_WIDTH}x{IMG_HEIGHT}/?{kw}&sig={sig}"
        dest = save_dir / f"{cat}_{done:04d}.jpg"

        if download_image(url, dest):
            done += 1
            if done % 30 == 0:
                print(f" {done}", end='', flush=True)
        attempts += 1

    status = "✓" if done == total else f"⚠ solo {done}"
    print(f"  {status}")
    return done


def split_val(cat: str) -> None:
    """Mueve el 20% de imágenes de train/ a val/ para una categoría."""
    imgs = list((TRAIN_DIR / cat).glob('*.jpg'))
    random.shuffle(imgs)
    n_val = max(1, int(len(imgs) * VAL_SPLIT))
    for p in imgs[:n_val]:
        shutil.move(str(p), str(VAL_DIR / cat / p.name))


def print_summary() -> None:
    print(f"\n{'Categoría':<28} {'Train':>7} {'Val':>7} {'Total':>7}")
    print("-" * 52)
    total_t = total_v = 0
    for cat in SCENE_CATEGORIES:
        t = len(list((TRAIN_DIR / cat).glob('*.jpg')))
        v = len(list((VAL_DIR   / cat).glob('*.jpg')))
        total_t += t
        total_v += v
        print(f"  {cat:<26} {t:>7} {v:>7} {t+v:>7}")
    print("-" * 52)
    print(f"  {'TOTAL':<26} {total_t:>7} {total_v:>7} {total_t+total_v:>7}")

    info = {
        'categories':  SCENE_CATEGORIES,
        'total_train': total_t,
        'total_val':   total_v,
        'source':      'Unsplash Source API',
        'img_size':    f'{IMG_WIDTH}x{IMG_HEIGHT}',
    }
    (DATASET_DIR / 'dataset_info.json').write_text(
        json.dumps(info, indent=2, ensure_ascii=False)
    )


def main() -> None:
    print("=" * 60)
    print("   DESCARGA DE DATASET - PTITU")
    print("   Fuente: Unsplash Source API (gratuita, sin clave)")
    print("=" * 60)
    print(f"\nCategorías  : {', '.join(SCENE_CATEGORIES)}")
    print(f"Por categoría: ~{int(TOTAL_PER_CAT*0.8)} train  +  ~{int(TOTAL_PER_CAT*0.2)} val")
    print(f"Total aprox. : {TOTAL_PER_CAT * len(SCENE_CATEGORIES)} imágenes")
    print("\nTiempo estimado: 15-25 min (depende de tu conexión)")
    print("\nPresiona Enter para iniciar, Ctrl+C para cancelar...")
    input()

    create_dirs()

    print("Descargando por categoría:\n")
    for cat in SCENE_CATEGORIES:
        download_category(cat, TOTAL_PER_CAT)

    print("\nDividiendo train / val (80/20)...")
    for cat in SCENE_CATEGORIES:
        split_val(cat)
        print(f"  ✓ {cat}")

    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print_summary()

    print(f"\n  Dataset guardado en: {DATASET_DIR}")
    print("\nSiguiente paso:")
    print("  python scripts/train_scene_classifier.py")
    print("=" * 60)


if __name__ == '__main__':
    random.seed(42)
    main()