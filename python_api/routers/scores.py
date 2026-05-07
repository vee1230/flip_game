from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class ScoreSubmit(BaseModel):
    player_id: Optional[int] = None
    firebase_uid: Optional[str] = None
    display_name: str
    score: int
    stage: str
    theme: str
    time_seconds: int
    moves: int


@router.get("/leaderboard")
def leaderboard(limit: int = 10):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT s.score, s.stage, s.theme, s.time_seconds, s.achieved_at,
                       p.display_name, p.account_type
                FROM scores s
                JOIN players p ON s.player_id = p.id
                ORDER BY s.score DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
    finally:
        db.close()


@router.post("/submit")
def submit_score(req: ScoreSubmit):
    if not req.player_id and not req.firebase_uid:
        raise HTTPException(status_code=400, detail="player_id or firebase_uid is required.")

    db = get_db()
    try:
        with db.cursor() as cursor:
            player_id = req.player_id

            # If firebase_uid provided, look up or create player
            if not player_id and req.firebase_uid:
                cursor.execute("SELECT id FROM players WHERE google_uid=%s", (req.firebase_uid,))
                row = cursor.fetchone()
                if row:
                    player_id = row["id"]
                else:
                    cursor.execute(
                        "INSERT INTO players (display_name, account_type, status, google_uid) VALUES (%s,'Google','Active',%s)",
                        (req.display_name, req.firebase_uid)
                    )
                    db.commit()
                    player_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO scores (player_id, score, stage, theme, time_seconds, moves) VALUES (%s,%s,%s,%s,%s,%s)",
                (player_id, req.score, req.stage, req.theme, req.time_seconds, req.moves)
            )
            db.commit()
            return {"success": True, "score_id": cursor.lastrowid}
    finally:
        db.close()
