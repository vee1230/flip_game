"""
routers/ml.py — FastAPI router exposing all 5 ML endpoints.

Endpoints:
  POST /api/v1/ml/predict-difficulty    → Best stage for player
  POST /api/v1/ml/classify-skill        → Beginner / Intermediate / Expert
  POST /api/v1/ml/predict-score         → Estimated score before playing
  POST /api/v1/ml/detect-cheat          → Is this score suspicious?
  POST /api/v1/ml/recommend-theme       → Best theme for player
  POST /api/v1/ml/train                 → Re-train models with latest DB data
  GET  /api/v1/ml/status                → Check if models are ready
"""

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from models.models import get_model, models_ready
from database import get_db

router = APIRouter()

# ── Shared constants ─────────────────────────────────────────
STAGES = ["Easy", "Medium", "Hard", "Expert"]
THEMES = ["Animals", "Food", "Space", "Nature", "Fantasy", "Sports"]
THEME_IDX = {t: i for i, t in enumerate(THEMES)}
STAGE_DIFFICULTY = {"Easy": 1, "Medium": 2, "Hard": 3, "Expert": 4}

SCORE_RANGES = {
    "Easy":   (1500, 2500),
    "Medium": (2200, 3200),
    "Hard":   (2800, 3700),
    "Expert": (3200, 4500),
}


def _derived(score: int, time_seconds: int, moves: int):
    return round(score / max(moves, 1), 2), round(score / max(time_seconds, 1), 2)


# ─────────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────────

class PlayerHistory(BaseModel):
    """Aggregated stats from a player's past games (caller can pre-compute or we fetch)."""
    player_id:    Optional[str] = None   # can be numeric ID or google_uid
    avg_score:    Optional[float] = None
    avg_time:     Optional[float] = None
    avg_moves:    Optional[float] = None
    last_theme:   Optional[str]  = "Animals"


class GameResult(BaseModel):
    """A single completed game result."""
    score:        int
    stage:        str
    theme:        str
    time_seconds: int
    moves:        int


# Helper: fetch player aggregate from DB
# ─────────────────────────────────────────────────────────────

def _fetch_player_stats(player_id: str) -> dict:
    db = get_db()
    try:
        with db.cursor() as c:
            # Check if player_id is numeric or string UID
            query = """
                SELECT AVG(s.score) as avg_score,
                       AVG(s.time_seconds) as avg_time,
                       AVG(s.moves) as avg_moves,
                       MAX(s.theme) as last_theme
                FROM scores s
                JOIN players p ON s.player_id = p.id
                WHERE p.id = %s OR p.google_uid = %s
            """
            c.execute(query, (player_id, player_id))
            row = c.fetchone()
            if not row or row["avg_score"] is None:
                return None
            return {
                "avg_score":  float(row["avg_score"]),
                "avg_time":   float(row["avg_time"]),
                "avg_moves":  float(row["avg_moves"]),
                "last_theme": row["last_theme"] or "Animals",
            }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# GET /status
# ─────────────────────────────────────────────────────────────

@router.get("/status")
def ml_status():
    return {
        "models_ready": models_ready(),
        "available_stages": STAGES,
        "available_themes": THEMES,
    }


# ─────────────────────────────────────────────────────────────
# 1. DIFFICULTY PREDICTOR
#    Recommends what stage the player should play next
# ─────────────────────────────────────────────────────────────

@router.post("/predict-difficulty")
def predict_difficulty(req: PlayerHistory):
    model   = get_model("difficulty")
    le      = get_model("stage_enc")

    # Resolve stats
    stats = None
    if req.player_id:
        stats = _fetch_player_stats(req.player_id)

    avg_score  = stats["avg_score"]  if stats else (req.avg_score  or 2000)
    avg_time   = stats["avg_time"]   if stats else (req.avg_time   or 30)
    avg_moves  = stats["avg_moves"]  if stats else (req.avg_moves  or 10)
    last_theme = stats["last_theme"] if stats else (req.last_theme or "Animals")

    spm, sps = _derived(int(avg_score), int(avg_time), int(avg_moves))
    theme_num = THEME_IDX.get(last_theme, 0)

    features = np.array([[theme_num, avg_score, avg_time, avg_moves, spm, sps]])
    pred_idx  = model.predict(features)[0]
    proba     = model.predict_proba(features)[0]

    recommended = le.inverse_transform([pred_idx])[0]
    confidence  = round(float(proba[pred_idx]) * 100, 1)

    return {
        "recommended_stage": recommended,
        "confidence_pct":    confidence,
        "probabilities": {
            stage: round(float(p) * 100, 1)
            for stage, p in zip(le.classes_, proba)
        },
        "reasoning": (
            f"Based on your average score of {int(avg_score)} "
            f"in {int(avg_time)}s with {int(avg_moves)} moves, "
            f"'{recommended}' is the best challenge for your skill level."
        )
    }


# ─────────────────────────────────────────────────────────────
# 2. SKILL CLASSIFIER
#    Classifies the player as Beginner / Intermediate / Expert
# ─────────────────────────────────────────────────────────────

@router.post("/classify-skill")
def classify_skill(req: GameResult):
    model = get_model("skill")
    le    = get_model("skill_enc")

    if req.stage not in STAGE_DIFFICULTY:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {req.stage}")

    stage_num = STAGE_DIFFICULTY[req.stage]
    theme_num = THEME_IDX.get(req.theme, 0)
    spm, sps  = _derived(req.score, req.time_seconds, req.moves)

    features  = np.array([[stage_num, theme_num, req.score,
                            req.time_seconds, req.moves, spm, sps]])
    pred_idx  = model.predict(features)[0]
    proba     = model.predict_proba(features)[0]
    skill     = le.inverse_transform([pred_idx])[0]
    confidence = round(float(proba[pred_idx]) * 100, 1)

    lo, hi = SCORE_RANGES[req.stage]
    efficiency = round((req.score - lo) / max(hi - lo, 1) * 100, 1)

    return {
        "skill_level":    skill,
        "confidence_pct": confidence,
        "efficiency_pct": efficiency,
        "probabilities": {
            s: round(float(p) * 100, 1)
            for s, p in zip(le.classes_, proba)
        },
        "badge": {
            "Beginner":     "🌱 Novice Player",
            "Intermediate": "⚡ Rising Star",
            "Expert":       "🏆 Master Player",
        }.get(skill, skill)
    }


# ─────────────────────────────────────────────────────────────
# 3. SCORE PREDICTOR
#    Predicts what score a player will get before they play
# ─────────────────────────────────────────────────────────────

class ScorePredictRequest(BaseModel):
    stage:              str
    theme:              str
    estimated_time:     Optional[int] = None  # player's avg time
    estimated_moves:    Optional[int] = None  # player's avg moves
    player_id:          Optional[str] = None


@router.post("/predict-score")
def predict_score(req: ScorePredictRequest):
    model = get_model("score")

    if req.stage not in STAGE_DIFFICULTY:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {req.stage}")

    # Resolve player history for better defaults
    time_s = req.estimated_time
    moves  = req.estimated_moves

    if req.player_id and (not time_s or not moves):
        stats = _fetch_player_stats(req.player_id)
        if stats:
            time_s = time_s or int(stats["avg_time"])
            moves  = moves  or int(stats["avg_moves"])

    stage_num = STAGE_DIFFICULTY[req.stage]
    theme_num = THEME_IDX.get(req.theme, 0)
    time_s    = time_s or 30
    moves     = moves  or 10

    features = np.array([[stage_num, theme_num, time_s, moves]])
    predicted = int(model.predict(features)[0])

    lo, hi = SCORE_RANGES[req.stage]
    predicted = max(lo, min(hi, predicted))  # clamp to range

    return {
        "predicted_score":  predicted,
        "stage":            req.stage,
        "theme":            req.theme,
        "score_range":      {"min": lo, "max": hi},
        "estimated_time_s": time_s,
        "estimated_moves":  moves,
        "message": (
            f"If you play {req.stage} ({req.theme}) in ~{time_s}s "
            f"with ~{moves} moves, you're predicted to score {predicted} points."
        )
    }


# ─────────────────────────────────────────────────────────────
# 4. CHEAT DETECTOR
#    Flags a submitted game result as normal or suspicious
# ─────────────────────────────────────────────────────────────

@router.post("/detect-cheat")
def detect_cheat(req: GameResult):
    model = get_model("cheat")

    spm, sps = _derived(req.score, req.time_seconds, req.moves)
    features = np.array([[req.score, req.time_seconds, req.moves, spm, sps]])
    result   = model.predict(features)[0]    # -1 = anomaly, 1 = normal
    score_f  = float(model.decision_function(features)[0])

    is_cheating  = (result == -1)
    anomaly_score = round(score_f, 4)

    # Rule-based sanity checks on top of ML
    flags = []
    lo, hi = SCORE_RANGES.get(req.stage, (1000, 5000))
    if req.score > hi * 1.15:
        flags.append("Score exceeds stage maximum by >15%")
    if req.time_seconds < 5:
        flags.append("Completion time suspiciously fast (<5s)")
    if req.moves < 3:
        flags.append("Too few moves for a memory match game")
    if req.score > 0 and req.time_seconds > 0 and sps > 300:
        flags.append("Score-per-second ratio is unrealistically high")

    final_flag = is_cheating or len(flags) > 0

    return {
        "is_suspicious":  final_flag,
        "ml_anomaly":     is_cheating,
        "anomaly_score":  anomaly_score,
        "rule_flags":     flags,
        "verdict":        "🚨 SUSPICIOUS" if final_flag else "✅ NORMAL",
        "details": (
            "This game result has been flagged for review."
            if final_flag else
            "This game result appears legitimate."
        )
    }


# ─────────────────────────────────────────────────────────────
# 5. THEME RECOMMENDER
#    Suggests the best theme for the player's next game
# ─────────────────────────────────────────────────────────────

class RecommendRequest(BaseModel):
    stage:      str
    player_id:  Optional[int] = None
    avg_score:  Optional[float] = None
    avg_time:   Optional[float] = None

@router.post("/recommend-theme")
def recommend_theme(req: RecommendRequest):
    model = get_model("theme")
    le    = get_model("theme_enc")

    if req.stage not in STAGE_DIFFICULTY:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {req.stage}")

    stats = None
    if req.player_id:
        stats = _fetch_player_stats(req.player_id)

    avg_score = stats["avg_score"] if stats else (req.avg_score or 2500)
    avg_time  = stats["avg_time"]  if stats else (req.avg_time  or 30)
    avg_moves = stats["avg_moves"] if stats else 10

    stage_num = STAGE_DIFFICULTY[req.stage]
    _, sps    = _derived(int(avg_score), int(avg_time), int(avg_moves))

    # Get top-3 theme recommendations using KNN probabilities
    proba     = model.predict_proba([[stage_num, 0, sps]])[0]
    top3_idx  = np.argsort(proba)[::-1][:3]
    top3      = [
        {"theme": le.inverse_transform([i])[0], "confidence_pct": round(float(proba[i]) * 100, 1)}
        for i in top3_idx
    ]
    best = top3[0]["theme"]

    return {
        "recommended_theme": best,
        "top_3_themes":      top3,
        "stage":             req.stage,
        "message": (
            f"For {req.stage} difficulty, '{best}' is the best theme "
            f"match for your play style!"
        )
    }


# ─────────────────────────────────────────────────────────────
# POST /train — Re-train with real DB data
# ─────────────────────────────────────────────────────────────

@router.post("/train")
def retrain_models():
    """Fetch all real scores from DB, blend with synthetic data, re-train."""
    import pandas as pd
    from ml.trainer import train_all, STAGE_DIFFICULTY, THEME_IDX

    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("""
                SELECT s.score, s.stage, s.theme, s.time_seconds, s.moves
                FROM scores s
                WHERE s.stage IS NOT NULL AND s.moves IS NOT NULL
            """)
            rows = c.fetchall()
    finally:
        db.close()

    extra_df = None
    if rows:
        df = pd.DataFrame(rows)
        df["stage_num"]      = df["stage"].map(STAGE_DIFFICULTY).fillna(1).astype(int)
        df["theme_num"]      = df["theme"].map(THEME_IDX).fillna(0).astype(int)
        df["score_per_move"] = (df["score"] / df["moves"].clip(1)).round(2)
        df["score_per_sec"]  = (df["score"] / df["time_seconds"].clip(1)).round(2)

        # derive skill label for real data too
        def skill_from_row(r):
            lo = {"Easy":1500,"Medium":2200,"Hard":2800,"Expert":3200}.get(r["stage"],1500)
            hi = {"Easy":2500,"Medium":3200,"Hard":3700,"Expert":4500}.get(r["stage"],4500)
            e  = (r["score"] - lo) / max(hi - lo, 1)
            return "Expert" if e >= 0.70 else ("Intermediate" if e >= 0.40 else "Beginner")

        df["skill_label"] = df.apply(skill_from_row, axis=1)
        extra_df = df

    from ml.models import load_models
    metrics = train_all(extra_df)
    load_models()   # reload fresh models into memory

    return {
        "success": True,
        "real_samples_used": len(rows),
        "metrics": metrics
    }
