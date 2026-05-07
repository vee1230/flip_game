"""
trainer.py — Generates synthetic training data and trains all 5 ML models.

Models Trained:
  1. Difficulty Predictor     → RandomForest Classifier
  2. Skill Classifier         → RandomForest Classifier
  3. Score Predictor          → GradientBoosting Regressor
  4. Cheat Detector           → IsolationForest (unsupervised)
  5. Theme Recommender        → KNN Classifier
"""

import os
import pickle
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, IsolationForest
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

# Where to save trained model files
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "trained")
os.makedirs(MODELS_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# Stage / Theme mappings
# ─────────────────────────────────────────────
STAGES  = ["Easy", "Medium", "Hard", "Expert"]
THEMES  = ["Animals", "Food", "Space", "Nature", "Fantasy", "Sports"]

STAGE_DIFFICULTY = {"Easy": 1, "Medium": 2, "Hard": 3, "Expert": 4}
THEME_IDX        = {t: i for i, t in enumerate(THEMES)}

# Score ranges per stage (realistic boundaries)
SCORE_RANGES = {
    "Easy":   (1500, 2500),
    "Medium": (2200, 3200),
    "Hard":   (2800, 3700),
    "Expert": (3200, 4500),
}
# Time ranges in seconds
TIME_RANGES = {
    "Easy":   (8,  30),
    "Medium": (12, 45),
    "Hard":   (18, 70),
    "Expert": (25, 120),
}
# Moves ranges
MOVES_RANGES = {
    "Easy":   (4,  12),
    "Medium": (6,  18),
    "Hard":   (8,  25),
    "Expert": (10, 35),
}


def _generate_synthetic_data(n: int = 800) -> pd.DataFrame:
    """Create a realistic synthetic dataset for training."""
    rng = np.random.default_rng(42)
    rows = []

    for _ in range(n):
        stage  = rng.choice(STAGES)
        theme  = rng.choice(THEMES)
        diff   = STAGE_DIFFICULTY[stage]

        lo_s, hi_s = SCORE_RANGES[stage]
        lo_t, hi_t = TIME_RANGES[stage]
        lo_m, hi_m = MOVES_RANGES[stage]

        score        = int(rng.integers(lo_s, hi_s))
        time_seconds = int(rng.integers(lo_t, hi_t))
        moves        = int(rng.integers(lo_m, hi_m))

        # Derived features
        score_per_move = score / max(moves, 1)
        score_per_sec  = score / max(time_seconds, 1)

        # Skill label: based on efficiency (score relative to stage ceiling)
        efficiency = (score - lo_s) / (hi_s - lo_s)   # 0-1
        if efficiency >= 0.70:
            skill = "Expert"
        elif efficiency >= 0.40:
            skill = "Intermediate"
        else:
            skill = "Beginner"

        rows.append({
            "stage":          stage,
            "stage_num":      diff,
            "theme":          theme,
            "theme_num":      THEME_IDX[theme],
            "score":          score,
            "time_seconds":   time_seconds,
            "moves":          moves,
            "score_per_move": round(score_per_move, 2),
            "score_per_sec":  round(score_per_sec,  2),
            "skill_label":    skill,
        })

    return pd.DataFrame(rows)


def train_all(extra_df: pd.DataFrame | None = None) -> dict:
    """
    Train all 5 models.  Pass `extra_df` (real DB rows) to blend with synthetic data.
    Returns a dict of evaluation metrics.
    """
    synthetic = _generate_synthetic_data(800)
    df = pd.concat([synthetic, extra_df], ignore_index=True) if extra_df is not None else synthetic

    # ── Feature sets ──────────────────────────────────────────
    FEAT_BASIC   = ["stage_num", "theme_num", "score", "time_seconds", "moves",
                    "score_per_move", "score_per_sec"]
    FEAT_NO_STAGE = ["theme_num", "score", "time_seconds", "moves",
                     "score_per_move", "score_per_sec"]

    metrics = {}

    # ──────────────────────────────────────────────────────────
    # 1. DIFFICULTY PREDICTOR
    #    Input : player's avg score, avg time, avg moves (no stage)
    #    Output: recommended stage
    # ──────────────────────────────────────────────────────────
    le_stage = LabelEncoder().fit(STAGES)
    X1 = df[FEAT_NO_STAGE]
    y1 = le_stage.transform(df["stage"])
    X1_tr, X1_te, y1_tr, y1_te = train_test_split(X1, y1, test_size=0.2, random_state=42)
    m1 = RandomForestClassifier(n_estimators=120, random_state=42)
    m1.fit(X1_tr, y1_tr)
    metrics["difficulty_predictor_acc"] = round(m1.score(X1_te, y1_te), 4)
    _save(m1,       "difficulty_model.pkl")
    _save(le_stage, "stage_encoder.pkl")

    # ──────────────────────────────────────────────────────────
    # 2. SKILL CLASSIFIER
    #    Input : all features
    #    Output: Beginner / Intermediate / Expert
    # ──────────────────────────────────────────────────────────
    le_skill = LabelEncoder().fit(["Beginner", "Intermediate", "Expert"])
    X2 = df[FEAT_BASIC]
    y2 = le_skill.transform(df["skill_label"])
    X2_tr, X2_te, y2_tr, y2_te = train_test_split(X2, y2, test_size=0.2, random_state=42)
    m2 = RandomForestClassifier(n_estimators=120, random_state=42)
    m2.fit(X2_tr, y2_tr)
    metrics["skill_classifier_acc"] = round(m2.score(X2_te, y2_te), 4)
    _save(m2,      "skill_model.pkl")
    _save(le_skill,"skill_encoder.pkl")

    # ──────────────────────────────────────────────────────────
    # 3. SCORE PREDICTOR
    #    Input : stage, theme, player history metrics
    #    Output: predicted score (regression)
    # ──────────────────────────────────────────────────────────
    X3 = df[["stage_num", "theme_num", "time_seconds", "moves"]]
    y3 = df["score"]
    X3_tr, X3_te, y3_tr, y3_te = train_test_split(X3, y3, test_size=0.2, random_state=42)
    m3 = GradientBoostingRegressor(n_estimators=120, learning_rate=0.1, random_state=42)
    m3.fit(X3_tr, y3_tr)
    metrics["score_predictor_r2"] = round(m3.score(X3_te, y3_te), 4)
    _save(m3, "score_model.pkl")

    # ──────────────────────────────────────────────────────────
    # 4. CHEAT DETECTOR (Anomaly Detection)
    #    Input : score, time_seconds, moves, ratios
    #    Output: -1 suspicious / 1 normal
    # ──────────────────────────────────────────────────────────
    X4 = df[["score", "time_seconds", "moves", "score_per_move", "score_per_sec"]]
    m4 = IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
    m4.fit(X4)
    metrics["cheat_detector_trained"] = True
    _save(m4, "cheat_model.pkl")

    # ──────────────────────────────────────────────────────────
    # 5. THEME RECOMMENDER
    #    Input : stage_num, skill level (encoded), recent theme
    #    Output: recommended theme
    # ──────────────────────────────────────────────────────────
    le_theme = LabelEncoder().fit(THEMES)
    X5 = df[["stage_num", "theme_num", "score_per_sec"]]
    y5 = le_theme.transform(df["theme"])
    m5 = KNeighborsClassifier(n_neighbors=7)
    m5.fit(X5, y5)
    metrics["theme_recommender_trained"] = True
    _save(m5,      "theme_model.pkl")
    _save(le_theme,"theme_encoder.pkl")

    print("[ML] All models trained successfully:", metrics)
    return metrics


def _save(obj, filename: str):
    path = os.path.join(MODELS_DIR, filename)
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    print(f"  Saved → {filename}")


if __name__ == "__main__":
    train_all()
