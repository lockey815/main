"""Model loading + inference.

The architecture is rebuilt from model/config.json (Keras 3 JSON) and the trained
weights are loaded from model/model.weights.h5. Nothing about the network (input
size, layers) is hardcoded: the input size is read from the config.

The network is a *whole-image classifier* (2-class softmax), not an object detector.
"Blast counting" is therefore done tile-by-tile: the smear is cut into model-sized
tiles, every tissue tile is classified, and tiles whose blast probability reaches
BLAST_PROB_THRESHOLD are counted as "suspected blast regions".
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps
import pypdfium2 as pdfium

from .config import Settings

os.environ.setdefault("KERAS_BACKEND", "tensorflow")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

log = logging.getLogger("leuknet.ml")

# ImageNet BGR channel means used by keras.applications.resnet50.preprocess_input
_RESNET_BGR_MEAN = np.array([103.939, 116.779, 123.68], dtype=np.float32)
# Tiles whose grayscale std-dev is below this are treated as empty background
_BACKGROUND_STD = 10.0
_MIN_SIDE = 32
_MAX_STAIN_TILE = 0.01  # tiles with less stained material than this are treated as foreign objects


class ModelNotReady(RuntimeError):
    pass


@dataclass
class ImageAnalysis:
    filename: str
    blast_count: int = 0
    tiles_analyzed: int = 0
    max_blast_probability: float = 0.0
    mean_blast_probability: float = 0.0
    foreign_objects: int = 0
    status: str = "normal"  # normal | blast_detected | unknown
    note: str = ""
    annotated_image: str = ""
    original_image: str = ""  # small preview, only used while reviewing (never stored in a report)


@dataclass
class ModelService:
    settings: Settings
    model: object = None
    input_h: int = 128
    input_w: int = 128
    info: dict = field(default_factory=dict)
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ------------------------------------------------------------------ loading
    def load(self) -> None:
        s = self.settings
        cfg_path, w_path = s.resolve(s.model_config_path), s.resolve(s.model_weights_path)
        meta_path = s.resolve(s.model_metadata_path)
        try:
            if not cfg_path.exists():
                raise FileNotFoundError(f"Missing {cfg_path}")
            if not w_path.exists():
                raise FileNotFoundError(
                    f"Missing {w_path}. Copy model.weights.h5 into backend/model/ (see README)."
                )
            import keras  # imported lazily so the API can start without TF for tooling

            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            model = keras.saving.deserialize_keras_object(cfg)
            model.load_weights(str(w_path))

            ishape = model.input_shape  # (None, H, W, C)
            self.input_h, self.input_w = int(ishape[1]), int(ishape[2])
            n_out = int(model.output_shape[-1])
            if n_out != len(s.class_list):
                raise ValueError(
                    f"Model has {n_out} outputs but CLASS_NAMES lists {len(s.class_list)}."
                )
            if not 0 <= s.blast_class_index < n_out:
                raise ValueError("BLAST_CLASS_INDEX is out of range for this model.")

            meta = {}
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.info = {
                "name": cfg.get("config", {}).get("name", "LeukNet"),
                "input_size": [self.input_h, self.input_w],
                "classes": s.class_list,
                "blast_class": s.class_list[s.blast_class_index],
                "preprocess_mode": s.preprocess_mode,
                "blast_probability_threshold": s.blast_prob_threshold,
                "keras_version": meta.get("keras_version"),
                "model_saved": meta.get("date_saved"),
            }
            self.model = model
            self.error = None
            # warm-up so the first real request is fast
            self.model.predict(
                np.zeros((1, self.input_h, self.input_w, 3), np.float32), verbose=0
            )
            log.info("Model loaded: %s", self.info)
        except Exception as exc:  # keep the API alive so /api/health explains the problem
            self.model = None
            self.error = f"{type(exc).__name__}: {exc}"
            log.exception("Model failed to load")

    @property
    def ready(self) -> bool:
        return self.model is not None

    # ------------------------------------------------------------ preprocessing
    def preprocess(self, batch: np.ndarray) -> np.ndarray:
        """batch: float32 RGB array in 0-255, shape (N, H, W, 3)."""
        mode = self.settings.preprocess_mode.lower()
        if mode == "resnet":
            return batch[..., ::-1] - _RESNET_BGR_MEAN  # RGB -> BGR, subtract mean
        if mode == "rescale":
            return batch / 255.0
        if mode == "none":
            return batch
        raise ValueError(f"Unknown PREPROCESS_MODE '{self.settings.preprocess_mode}'")

    def predict_blast_probs(self, batch: np.ndarray) -> np.ndarray:
        if not self.ready:
            raise ModelNotReady(self.error or "Model not loaded")
        x = self.preprocess(batch.astype(np.float32))
        with self._lock:  # Keras models are not guaranteed thread-safe
            probs = self.model.predict(x, batch_size=32, verbose=0)
        return np.asarray(probs)[:, self.settings.blast_class_index]

    # ----------------------------------------------------------------- analysis
    def expand_upload(self, filename: str, raw: bytes, content_type: str) -> list[tuple[str, Image.Image | None, str]]:
        """-> [(sample_name, PIL image or None, error_note)]. PDFs become one sample per page."""
        if content_type == "application/pdf" or raw[:5] == b"%PDF-":
            try:
                pdf = pdfium.PdfDocument(raw)
                out = []
                for i in range(min(len(pdf), self.settings.max_pdf_pages)):
                    pil = pdf[i].render(scale=2).to_pil().convert("RGB")
                    out.append((f"{filename} (page {i + 1})", pil, ""))
                return out or [(filename, None, "The PDF has no pages.")]
            except Exception:
                return [(filename, None, "The PDF could not be read.")]
        try:
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
            return [(filename, img, "")]
        except Exception:
            return [(filename, None, "File is not a readable image.")]

    def analyze_image(self, filename: str, img: Image.Image | None, error: str = "") -> ImageAnalysis:
        s = self.settings
        if img is None:
            return ImageAnalysis(filename, status="unknown", note=error or "File could not be read.")
        if min(img.size) < _MIN_SIDE:
            return ImageAnalysis(filename, status="unknown", note="Image is too small to analyse.")

        longest = max(img.size)
        if longest > s.max_image_side:
            scale = s.max_image_side / longest
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)

        original = self._encode(img, 512, 70)

        # --- "Unknown": blurred images or content that is not a stained smear ---
        if _laplacian_variance(img) < s.blur_threshold:
            return ImageAnalysis(filename, status="unknown", original_image=original, annotated_image=original,
                                 note="The image is too blurred to analyse. Upload a sharper image.")
        if s.min_stain_fraction > 0 and _stain_fraction(np.asarray(img.convert("HSV"))) < s.min_stain_fraction:
            return ImageAnalysis(filename, status="unknown", original_image=original, annotated_image=original,
                                 note="This does not look like a stained blood smear (no stained cells found).")

        tiles, boxes, foreign_boxes = self._make_tiles(img)
        if not tiles:
            return ImageAnalysis(
                filename, status="unknown", original_image=original, annotated_image=self._encode(img),
                foreign_objects=len(foreign_boxes),
                note="No analysable cells found: the image looks empty or contains only non-cellular material.",
            )

        probs = self.predict_blast_probs(np.stack(tiles))
        flagged = probs >= s.blast_prob_threshold
        blast_count = int(flagged.sum())

        annotated = img.copy()
        draw = ImageDraw.Draw(annotated)
        width = max(2, round(max(img.size) / 400))
        for (x0, y0, x1, y1), p, hit in zip(boxes, probs, flagged):
            if hit:
                draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 40, 40), width=width)
                draw.text((x0 + 3, y0 + 2), f"{p:.0%}", fill=(255, 255, 0))
        for x0, y0, x1, y1 in foreign_boxes:
            draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(255, 170, 0), width=width)

        return ImageAnalysis(
            filename=filename,
            blast_count=blast_count,
            tiles_analyzed=len(tiles),
            max_blast_probability=round(float(probs.max()), 4),
            mean_blast_probability=round(float(probs.mean()), 4),
            foreign_objects=len(foreign_boxes),
            status="blast_detected" if blast_count else "normal",
            original_image=original,
            annotated_image=self._encode(annotated),
        )

    def _make_tiles(self, img: Image.Image):
        h, w = self.input_h, self.input_w
        arr = np.asarray(img, dtype=np.float32)
        H, W = arr.shape[:2]

        # Small image (e.g. a single-cell crop): classify the whole image as one tile.
        if max(H, W) <= int(1.5 * max(h, w)):
            tile = np.asarray(img.resize((w, h), Image.BILINEAR), dtype=np.float32)
            return [tile], [(0, 0, W, H)], []

        hsv = np.asarray(img.convert("HSV"))
        stride = self.settings.tile_stride or w
        xs = list(range(0, W - w + 1, stride))
        ys = list(range(0, H - h + 1, stride))
        if xs[-1] + w < W:
            xs.append(W - w)  # cover the right edge
        if ys[-1] + h < H:
            ys.append(H - h)  # cover the bottom edge

        tiles, boxes, foreign = [], [], []
        for y in ys:
            for x in xs:
                t = arr[y : y + h, x : x + w]
                if t.mean(axis=2).std() < _BACKGROUND_STD:
                    continue  # empty background
                if self.settings.foreign_object_check and _stain_fraction(hsv[y : y + h, x : x + w]) < _MAX_STAIN_TILE:
                    foreign.append((x, y, x + w, y + h))  # texture but no stained material
                    continue
                tiles.append(t)
                boxes.append((x, y, x + w, y + h))
        return tiles, boxes, foreign

    @staticmethod
    def _encode(img: Image.Image, max_side: int = 1024, quality: int = 82) -> str:
        img = img.copy()
        img.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _stain_fraction(hsv: np.ndarray) -> float:
    """Fraction of pixels with the purple/blue/pink colours of a Wright/Giemsa-stained smear.
    PIL HSV: H,S,V in 0-255 (hue 0-255 = 0-360 degrees)."""
    h, s = hsv[..., 0], hsv[..., 1]
    stained = (s > 45) & ((h >= 140) | (h <= 12))
    return float(stained.mean())


def _laplacian_variance(img: Image.Image) -> float:
    g = img.convert("L")
    g.thumbnail((512, 512))
    a = np.asarray(g, dtype=np.float32)
    lap = 4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    return float(lap.var())
