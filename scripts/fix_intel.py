"""
Parche para copiar paisajes y exteriores del dataset Intel
que ya está descargado en cache de kagglehub.

Uso:
    python scripts/fix_intel.py
"""
import sys
import shutil
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.core.config import DATA_DIR

TRAIN_DIR = DATA_DIR / 'dataset' / 'train'
VAL_DIR   = DATA_DIR / 'dataset' / 'val'
LIMIT     = 150
VAL_SPLIT = 0.20
SEED      = 42

INTEL_MAPPING = {
    'buildings': 'exteriores',
    'street':    'exteriores',
    'forest':    'paisajes',
    'glacier':   'paisajes',
    'mountain':  'paisajes',
    'sea':       'paisajes',
}

def copy_images(sources, dest_dir, prefix, start_idx=0):
    copied = 0
    for i, src in enumerate(sources):
        dest = dest_dir / f"{prefix}_{start_idx + i:04d}{src.suffix.lower()}"
        try:
            shutil.copy2(src, dest)
            copied += 1
        except Exception as e:
            print(f"  ⚠ {e}")
    return copied

def split_val(cat):
    imgs  = list((TRAIN_DIR / cat).glob('*.*'))
    # No mover las que ya están en val
    n_val = max(1, int(len(imgs) * VAL_SPLIT))
    random.shuffle(imgs)
    moved = 0
    for p in imgs[:n_val]:
        dst = VAL_DIR / cat / p.name
        if not dst.exists():
            shutil.move(str(p), str(dst))
            moved += 1
    return moved

def main():
    random.seed(SEED)

    import kagglehub
    path = Path(kagglehub.dataset_download(
        'puneet6060/intel-image-classification'
    ))
    print(f"Dataset en: {path}\n")

    counts = {'exteriores': 0, 'paisajes': 0}

    # La estructura real es seg_train/seg_train/<clase>/
    # También revisamos seg_test/seg_test/<clase>/
    for top in ['seg_train', 'seg_test']:
        top_dir = path / top / top
        if not top_dir.exists():
            top_dir = path / top          # fallback nivel simple
        if not top_dir.exists():
            continue

        for class_dir in top_dir.iterdir():
            if not class_dir.is_dir():
                continue
            class_name = class_dir.name.lower()
            mapped_cat = INTEL_MAPPING.get(class_name)
            if mapped_cat is None:
                continue

            already = len(list((TRAIN_DIR / mapped_cat).glob('*.*')))
            remaining = max(0, LIMIT - already)
            if remaining == 0:
                continue

            images = [p for p in class_dir.rglob('*')
                      if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
            random.shuffle(images)
            images = images[:remaining]

            n = copy_images(images, TRAIN_DIR / mapped_cat,
                            prefix=mapped_cat, start_idx=already)
            counts[mapped_cat] += n
            print(f"  {class_name:<15} → {mapped_cat:<12}  +{n} imágenes")

    print("\nDividiendo en val (20%)...")
    for cat in ['exteriores', 'paisajes']:
        moved = split_val(cat)
        t = len(list((TRAIN_DIR / cat).glob('*.*')))
        v = len(list((VAL_DIR   / cat).glob('*.*')))
        print(f"  {cat:<28} train={t}  val={v}")

    print("\n✓ Parche aplicado. Verifica con:")
    print("  python scripts/train_scene_classifier.py")

if __name__ == '__main__':
    main()