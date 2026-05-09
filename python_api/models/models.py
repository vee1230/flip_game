"""
models.py — Lazy-loads all trained ML model files from disk.
Call load_models() once on app startup, then use get_model(name).
"""

import os
import pickle

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "trained")

_cache: dict = {}

MODEL_FILES = {
    "difficulty": "difficulty_model.pkl",
    "stage_enc":  "stage_encoder.pkl",
    "skill":      "skill_model.pkl",
    "skill_enc":  "skill_encoder.pkl",
    "score":      "score_model.pkl",
    "cheat":      "cheat_model.pkl",
    "theme":      "theme_model.pkl",
    "theme_enc":  "theme_encoder.pkl",
}


def load_models():
    """Load all pickled models into memory. Called at FastAPI startup."""
    for key, filename in MODEL_FILES.items():
        path = os.path.join(MODELS_DIR, filename)
        if os.path.exists(path):
            with open(path, "rb") as f:
                _cache[key] = pickle.load(f)
            print(f"[ML] Loaded model: {key}")
        else:
            print(f"[ML] WARNING: model file not found → {filename}")


def get_model(name: str):
    """Return a loaded model by key. Raises RuntimeError if not loaded."""
    if name not in _cache:
        raise RuntimeError(
            f"Model '{name}' is not loaded. "
            "Did you run the trainer first? (python -m ml.trainer)"
        )
    return _cache[name]


def get_model_safe(name: str):
    """Return a loaded model by key, or None if not available. Never raises."""
    return _cache.get(name, None)


def models_ready() -> bool:
    """Returns True if all models are loaded and ready."""
    return all(k in _cache for k in MODEL_FILES)
