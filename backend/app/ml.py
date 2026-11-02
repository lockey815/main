
"""Model loading + inference.

The complete Keras model is downloaded from Hugging Face:
Lockey815/LeukNet-ResNet50/resnet50_final.keras

The model is a whole-image classifier (2-class softmax), not an
object detector. Blast counting is performed tile-by-tile.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import threading
from dataclasses import dataclass, field
import keras
import huggingface_hub
from huggingface_hub import hf_hub_download

import numpy as np
from PIL import Image, ImageDraw, ImageOps
import pypdfium2 as pdfium

from .config import Settings

os.environ.setdefault("KERAS_BACKEND", "tensorflow")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

log = logging.getLogger("leuknet.ml")

MODEL_REPO = os.getenv(
    "HF_MODEL_REPO",
    "Lockey815/LeukNet-ResNet50",
)

MODEL_FILENAME = os.getenv(
    "HF_MODEL_FILENAME",
    "model.weights.h5",
)

_RESNET_BGR_MEAN = np.array(
    [103.939, 116.779, 123.68],
    dtype=np.float32,
)

_BACKGROUND_STD = 10.0
_MIN_SIDE = 32
_MAX_STAIN_TILE = 0.01


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
    status: str = "normal"
    note: str = ""
    annotated_image: str = ""
    original_image: str = ""


@dataclass
class ModelService:
    settings: Settings
    model: object = None
    input_h: int = 128
    input_w: int = 128
    info: dict = field(default_factory=dict)
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ---------------------------------------------------------------
    # Model loading from Hugging Face
    # ---------------------------------------------------------------

    def load(self) -> None:
        try:

config_path = hf_hub_download(
    repo_id=MODEL_REPO,
    filename="config.json"
)

weights_path = hf_hub_download(
    repo_id=MODEL_REPO,
    filename="model.weights.h5"
)

with open(config_path, "r") as f:
    model_config = json.load(f)

model = keras.models.model_from_json(
    json.dumps(model_config)
)

model.load_weights(weights_path)
            # Validate model input dimensions
            ishape = model.input_shape

            if isinstance(ishape, list):
                raise ValueError(
                    "Multiple-input models are not supported."
                )

            if len(ishape) != 4:
                raise ValueError(
                    f"Expected a 4D image input, got {ishape}"
                )

            if ishape[1] is None or ishape[2] is None:
                raise ValueError(
                    f"Dynamic image dimensions are not supported: {ishape}"
                )

            if ishape[-1] != 3:
                raise ValueError(
                    f"Expected 3-channel RGB input, got {ishape}"
                )

            self.input_h = int(ishape[1])
            self.input_w = int(ishape[2])

            # Validate output classes
            oshape = model.output_shape

            if isinstance(oshape, list):
                raise ValueError(
                    "Multiple-output models are not supported."
                )

            n_out = int(oshape[-1])

            if n_out != len(self.settings.class_list):
                raise ValueError(
                    f"Model has {n_out} outputs but "
                    f"CLASS_NAMES lists "
                    f"{len(self.settings.class_list)}."
                )

            if not 0 <= self.settings.blast_class_index < n_out:
                raise ValueError(
                    "BLAST_CLASS_INDEX is out of range."
                )

            # Load optional local metadata
            meta_path = self.settings.resolve(
                self.settings.model_metadata_path
            )

            meta = {}

            if meta_path.exists():
                meta = json.loads(
                    meta_path.read_text(encoding="utf-8")
                )

            self.info = {
                "name": model.name or "LeukNet",
                "input_size": [
                    self.input_h,
                    self.input_w,
                ],
                "classes": self.settings.class_list,
                "blast_class": self.settings.class_list[
                    self.settings.blast_class_index
                ],
                "preprocess_mode": self.settings.preprocess_mode,
                "blast_probability_threshold": (
                    self.settings.blast_prob_threshold
                ),
                "keras_version": meta.get("keras_version"),
                "model_saved": meta.get("date_saved"),
                "source": f"{MODEL_REPO}/{MODEL_FILENAME}",
            }

            self.model = model
            self.error = None

            # Warm-up inference
            self.model.predict(
                np.zeros(
                    (1, self.input_h, self.input_w, 3),
                    dtype=np.float32,
                ),
                verbose=0,
            )

            log.info(
                "LeukNet model loaded successfully: %s",
                self.info,
            )

        except Exception as exc:
            self.model = None
            self.error = f"{type(exc).__name__}: {exc}"
            log.exception("Model failed to load")

    @property
    def ready(self) -> bool:
        return self.model is not None

    # ---------------------------------------------------------------
    # Preprocessing
    # ---------------------------------------------------------------

    def preprocess(self, batch: np.ndarray) -> np.ndarray:
        """Input: float32 RGB array, 0-255, shape (N,H,W,3)."""

        mode = self.settings.preprocess_mode.lower()

        if mode == "resnet":
            return batch[..., ::-1] - _RESNET_BGR_MEAN

        if mode == "rescale":
            return batch / 255.0

        if mode == "none":
            return batch

        raise ValueError(
            f"Unknown PREPROCESS_MODE '{self.settings.preprocess_mode}'"
        )

    def predict_blast_probs(self, batch: np.ndarray) -> np.ndarray:
        if not self.ready:
            raise ModelNotReady(
                self.error or "Model not loaded"
            )

        x = self.preprocess(
            batch.astype(np.float32)
        )

        with self._lock:
            probs = self.model.predict(
                x,
                batch_size=32,
                verbose=0,
            )

        return np.asarray(probs)[:, self.settings.blast_class_index]

    # ---------------------------------------------------------------
    # Image upload processing
    # ---------------------------------------------------------------

    def expand_upload(
        self,
        filename: str,
        raw: bytes,
        content_type: str,
    ) -> list[tuple[str, Image.Image | None, str]]:

        if content_type == "application/pdf" or raw[:5] == b"%PDF-":
            try:
                pdf = pdfium.PdfDocument(raw)
                out = []

                for i in range(
                    min(len(pdf), self.settings.max_pdf_pages)
                ):
                    pil = (
                        pdf[i]
                        .render(scale=2)
                        .to_pil()
                        .convert("RGB")
                    )

                    out.append(
                        (f"{filename} (page {i + 1})", pil, "")
                    )

                return out or [
                    (filename, None, "The PDF has no pages.")
                ]

            except Exception:
                log.exception("PDF processing failed")
                return [
                    (filename, None, "The PDF could not be read.")
                ]

        try:
            img = ImageOps.exif_transpose(
                Image.open(io.BytesIO(raw))
            ).convert("RGB")

            return [(filename, img, "")]

        except Exception:
            return [
                (filename, None, "File is not a readable image.")
            ]

    # ---------------------------------------------------------------
    # Image analysis
    # ---------------------------------------------------------------

    def analyze_image(
        self,
        filename: str,
        img: Image.Image | None,
        error: str = "",
    ) -> ImageAnalysis:

        s = self.settings

        if img is None:
            return ImageAnalysis(
                filename,
                status="unknown",
                note=error or "File could not be read.",
            )

        if min(img.size) < _MIN_SIDE:
            return ImageAnalysis(
                filename,
                status="unknown",
                note="Image is too small to analyse.",
            )

        longest = max(img.size)

        if longest > s.max_image_side:
            scale = s.max_image_side / longest

            img = img.resize(
                (
                    round(img.width * scale),
                    round(img.height * scale),
                ),
                Image.LANCZOS,
            )

        original = self._encode(img, 512, 70)

        if _laplacian_variance(img) < s.blur_threshold:
            return ImageAnalysis(
                filename,
                status="unknown",
                original_image=original,
                annotated_image=original,
                note="The image is too blurred to analyse. Upload a sharper image.",
            )

        if (
            s.min_stain_fraction > 0
            and _stain_fraction(
                np.asarray(img.convert("HSV"))
            ) < s.min_stain_fraction
        ):
            return ImageAnalysis(
                filename,
                status="unknown",
                original_image=original,
                annotated_image=original,
                note="This does not look like a stained blood smear (no stained cells found).",
            )

        tiles, boxes, foreign_boxes = self._make_tiles(img)

        if not tiles:
            return ImageAnalysis(
                filename,
                status="unknown",
                original_image=original,
                annotated_image=self._encode(img),
                foreign_objects=len(foreign_boxes),
                note="No analysable cells found: the image looks empty or contains only non-cellular material.",
            )

        probs = self.predict_blast_probs(
            np.stack(tiles)
        )

        flagged = probs >= s.blast_prob_threshold
        blast_count = int(flagged.sum())

        annotated = img.copy()
        draw = ImageDraw.Draw(annotated)

        width = max(
            2,
            round(max(img.size) / 400),
        )

        for (x0, y0, x1, y1), p, hit in zip(
            boxes,
            probs,
            flagged,
        ):
            if hit:
                draw.rectangle(
                    [x0, y0, x1 - 1, y1 - 1],
                    outline=(255, 40, 40),
                    width=width,
                )

                draw.text(
                    (x0 + 3, y0 + 2),
                    f"{p:.0%}",
                    fill=(255, 255, 0),
                )

        for x0, y0, x1, y1 in foreign_boxes:
            draw.rectangle(
                [x0, y0, x1 - 1, y1 - 1],
                outline=(255, 170, 0),
                width=width,
            )

        return ImageAnalysis(
            filename=filename,
            blast_count=blast_count,
            tiles_analyzed=len(tiles),
            max_blast_probability=round(
                float(probs.max()), 4
            ),
            mean_blast_probability=round(
                float(probs.mean()), 4
            ),
            foreign_objects=len(foreign_boxes),
            status=(
                "blast_detected" if blast_count else "normal"
            ),
            original_image=original,
            annotated_image=self._encode(annotated),
        )

    # ---------------------------------------------------------------
    # Tile generation
    # ---------------------------------------------------------------

    def _make_tiles(self, img: Image.Image):

        h, w = self.input_h, self.input_w

        arr = np.asarray(
            img,
            dtype=np.float32,
        )

        H, W = arr.shape[:2]

        if max(H, W) <= int(1.5 * max(h, w)):
            tile = np.asarray(
                img.resize(
                    (w, h),
                    Image.BILINEAR,
                ),
                dtype=np.float32,
            )

            return [tile], [(0, 0, W, H)], []

        hsv = np.asarray(img.convert("HSV"))

        stride = self.settings.tile_stride or w

        xs = list(range(0, W - w + 1, stride))
        ys = list(range(0, H - h + 1, stride))

        if xs[-1] + w < W:
            xs.append(W - w)

        if ys[-1] + h < H:
            ys.append(H - h)

        tiles = []
        boxes = []
        foreign = []

        for y in ys:
            for x in xs:

                t = arr[y:y + h, x:x + w]

                if t.mean(axis=2).std() < _BACKGROUND_STD:
                    continue

                if (
                    self.settings.foreign_object_check
                    and _stain_fraction(
                        hsv[y:y + h, x:x + w]
                    ) < _MAX_STAIN_TILE
                ):
                    foreign.append(
                        (x, y, x + w, y + h)
                    )
                    continue

                tiles.append(t)
                boxes.append(
                    (x, y, x + w, y + h)
                )

        return tiles, boxes, foreign

    # ---------------------------------------------------------------
    # Image encoding
    # ---------------------------------------------------------------

    @staticmethod
    def _encode(
        img: Image.Image,
        max_side: int = 1024,
        quality: int = 82,
    ) -> str:

        img = img.copy()
        img.thumbnail((max_side, max_side))

        buf = io.BytesIO()

        img.save(
            buf,
            "JPEG",
            quality=quality,
        )

        return (
            "data:image/jpeg;base64,"
            + base64.b64encode(buf.getvalue()).decode()
        )


# ---------------------------------------------------------------
# Image quality and stain helpers
# ---------------------------------------------------------------

def _stain_fraction(hsv: np.ndarray) -> float:
    """Estimate stained pixels in a Wright/Giemsa blood smear."""

    h, s = hsv[..., 0], hsv[..., 1]

    stained = (
        (s > 45)
        & ((h >= 140) | (h <= 12))
    )

    return float(stained.mean())


def _laplacian_variance(img: Image.Image) -> float:
    """Estimate image sharpness using Laplacian variance."""

    g = img.convert("L")
    g.thumbnail((512, 512))

    a = np.asarray(
        g,
        dtype=np.float32,
    )

    lap = (
        4 * a[1:-1, 1:-1]
        - a[:-2, 1:-1]
        - a[2:, 1:-1]
        - a[1:-1, :-2]
        - a[1:-1, 2:]
    )

    return float(lap.var())
