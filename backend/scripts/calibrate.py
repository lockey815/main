"""Find the right PREPROCESS_MODE and BLAST_CLASS_INDEX for YOUR retrained model.

config.json describes the layers but not how images were scaled during training or
which output index is "blast". This script tests every combination on a small,
labelled set of images you know the answer for and tells you what to put in .env.

Folder layout (any number of images, ~20+ per class is plenty):

    calib/
      blast/       <- images that contain blast cells (leukemic)
      non_blast/   <- healthy / non-leukemic images

Run from the backend/ folder:

    python scripts/calibrate.py calib --blast-folder blast
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402
from app.ml import ModelService  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--blast-folder", default="blast", help="name of the sub-folder holding blast images")
    args = ap.parse_args()

    svc = ModelService(get_settings())
    svc.load()
    if not svc.ready:
        sys.exit(f"Model failed to load: {svc.error}")

    X, y = [], []
    for sub in sorted(p for p in Path(args.folder).iterdir() if p.is_dir()):
        label = 1 if sub.name == args.blast_folder else 0
        for f in sub.iterdir():
            if f.suffix.lower() in EXTS:
                im = Image.open(f).convert("RGB").resize((svc.input_w, svc.input_h), Image.BILINEAR)
                X.append(np.asarray(im, dtype=np.float32))
                y.append(label)
    if len(set(y)) < 2:
        sys.exit("Need images in both a blast folder and at least one non-blast folder.")
    X, y = np.stack(X), np.array(y)
    print(f"{len(y)} images ({int(y.sum())} blast / {int((1 - y).sum())} non-blast)\n")

    rows = []
    for mode in ("resnet", "rescale", "none"):
        svc.settings.preprocess_mode = mode
        probs = svc.model.predict(svc.preprocess(X), batch_size=32, verbose=0)
        for idx in range(probs.shape[1]):
            pred = (probs[:, idx] >= 0.5).astype(int)
            tpr = float((pred[y == 1] == 1).mean())
            tnr = float((pred[y == 0] == 0).mean())
            rows.append((0.5 * (tpr + tnr), mode, idx, tpr, tnr, float(probs[:, idx].std())))

    rows.sort(reverse=True)
    print(f"{'balanced acc':>12}  {'PREPROCESS_MODE':<16}{'BLAST_CLASS_INDEX':<19}{'sens':>6}{'spec':>7}{'prob std':>10}")
    for bal, mode, idx, tpr, tnr, sd in rows:
        print(f"{bal:12.3f}  {mode:<16}{idx:<19}{tpr:6.2f}{tnr:7.2f}{sd:10.3f}")
    best = rows[0]
    print(f"\n=> put in backend/.env:\n   PREPROCESS_MODE={best[1]}\n   BLAST_CLASS_INDEX={best[2]}")
    if best[0] < 0.75:
        print("\nWARNING: best balanced accuracy is low. Check that the labelled images are correct, "
              "and that the weights file is the retrained one that matches config.json.")


if __name__ == "__main__":
    main()
