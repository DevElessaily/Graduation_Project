from __future__ import annotations
import logging, os, re, unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ـ": None})
_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PUNCT = str.maketrans({"٫": ".", "٬": ",", "،": ",", "\u200f": None, "\u200e": None, "\u00a0": " "})
_DIAC = re.compile(r"[\u064B-\u065F\u0670]")

def normalize_for_ml(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DIG).translate(_PUNCT).translate(_FOLD)
    text = _DIAC.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()

_DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models"

class MLSMSClassifier:
    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir) if model_dir else Path(
            os.getenv("SMS_ML_MODEL_DIR", str(_DEFAULT_MODEL_DIR)))
        self._bin = self._cat = None
        self._available = None

    def _ensure_loaded(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import onnxruntime as ort
        except ImportError:
            self._available = False
            return False
        bp = self.model_dir / "is_transaction.onnx"
        cp = self.model_dir / "category.onnx"
        if not bp.exists() or not cp.exists():
            self._available = False
            return False
        try:
            self._bin = ort.InferenceSession(str(bp))
            self._cat = ort.InferenceSession(str(cp))
        except Exception:
            self._available = False
            return False
        self._available = True
        return True

    @property
    def available(self):
        return self._ensure_loaded()

    def is_transaction(self, text):
        if not self._ensure_loaded():
            return None
        import numpy as np
        arr = np.array([normalize_for_ml(text)], dtype=str)
        out = self._bin.run(None, {self._bin.get_inputs()[0].name: arr})
        label = out[0][0]
        proba = out[1][0] if len(out) > 1 else None  # dict {0: p, 1: p} for LR
        if isinstance(proba, dict):
            score = float(proba.get(1, proba.get("1", 0.0)))
            is_tx = (score >= 0.5) if label is None else (str(label).lower() in ("1", "true") or bool(label))
        else:
            is_tx = bool(label) if not isinstance(label, str) else str(label).lower() in ("1", "true")
            score = float(proba[1]) if (proba is not None and len(proba) > 1) else 0.0
        return is_tx, score

    def category(self, text):
        if not self._ensure_loaded():
            return None
        import numpy as np
        arr = np.array([normalize_for_ml(text)], dtype=str)
        out = self._cat.run(None, {self._cat.get_inputs()[0].name: arr})
        label = out[0][0]
        proba = out[1][0] if len(out) > 1 else None  # dict {class: prob} for LR
        if isinstance(proba, dict):
            score = float(max(proba.values())) if proba else 0.0
        else:
            score = float(max(proba)) if proba is not None else 0.0
        return str(label), score

_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = MLSMSClassifier()
    return _classifier
