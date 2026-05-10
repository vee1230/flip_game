from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date
from database import get_db

router = APIRouter()

class ClaimRequest(BaseModel):
    player_id: int

class CompleteChallengeRequest(BaseModel):
    difficulty: str
    matched_pairs: int
    is_completed: bool

@router.post("/claim")
def claim_daily_challenge(req: ClaimRequest):
    """
    Claim the Daily Challenge reward.
    - Requires an existing daily_challenges record with is_completed=1 and is_claimed=0.
    - Adds 50 stars to the player's balance.
    """
    db = get_db()
    today = date.today().isoformat()
    try:
        with db.cursor() as cursor:
            # Check if record for today exists
            cursor.execute(
                "SELECT id, is_completed, is_claimed FROM daily_challenges WHERE player_id = %s AND date = %s FOR UPDATE",
                (req.player_id, today)
            )
            challenge = cursor.fetchone()

            if not challenge or not challenge["is_completed"]:
                raise HTTPException(status_code=400, detail="Daily Challenge is not completed yet.")

            if challenge["is_claimed"]:
                raise HTTPException(status_code=400, detail="Daily Challenge already claimed today.")

            reward_amount = 50

            # If not claimed, update the stars
            cursor.execute(
                "UPDATE players SET stars = stars + %s WHERE id = %s",
                (reward_amount, req.player_id)
            )

            # Record the claim in daily_challenges
            cursor.execute(
                "UPDATE daily_challenges SET is_claimed = 1, claimed_at = NOW() WHERE id = %s",
                (challenge["id"],)
            )

            # Fetch the updated stars balance
            cursor.execute("SELECT stars FROM players WHERE id = %s", (req.player_id,))
            row = cursor.fetchone()
            total_stars = row["stars"] if row else reward_amount

            db.commit()
            return {
                "success": True,
                "message": "Daily Challenge reward claimed successfully",
                "stars_added": reward_amount,
                "total_stars": total_stars,
                "claimed_today": True
            }
    finally:
        db.close()

@router.post("/complete/{uid}")
def complete_daily_challenge(uid: str, req: CompleteChallengeRequest):
    """
    Mark the daily challenge as completed for today.
    Requires matched_pairs >= 3 for Easy Mode.
    """
    if req.matched_pairs is None or not isinstance(req.matched_pairs, int) or req.matched_pairs < 0:
        raise HTTPException(status_code=400, detail="Invalid matched_pairs value")
    if req.matched_pairs > 8:
        raise HTTPException(status_code=400, detail="matched_pairs exceeds maximum possible pairs")

    if req.matched_pairs < 3:
        return {"status": "error", "message": "Not enough pairs matched to complete the challenge."}

    db = get_db()
    today = date.today().isoformat()
    try:
        with db.cursor() as cursor:
            # Resolve UID to player ID safely
            cursor.execute("SELECT id FROM players WHERE id = %s OR google_uid = %s", (uid, uid))
            player = cursor.fetchone()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")
            
            player_id = player["id"]

            cursor.execute(
                "SELECT id FROM daily_challenges WHERE player_id = %s AND date = %s FOR UPDATE",
                (player_id, today)
            )
            challenge = cursor.fetchone()

            if challenge:
                cursor.execute(
                    "UPDATE daily_challenges SET is_completed = 1, matched_pairs = GREATEST(IFNULL(matched_pairs, 0), %s), completed_at = NOW() WHERE id = %s",
                    (req.matched_pairs, challenge["id"])
                )
            else:
                cursor.execute(
                    "INSERT INTO daily_challenges (player_id, date, is_completed, is_claimed, matched_pairs, completed_at) VALUES (%s, %s, 1, 0, %s, NOW())",
                    (player_id, today, req.matched_pairs)
                )

            db.commit()
            return {"status": "success", "message": "Challenge marked as completed."}
    finally:
        db.close()

@router.get("/status/{uid}")
def get_daily_challenge_status(uid: str):
    """
    Fetch the status of today's daily challenge.
    """
    db = get_db()
    today = date.today().isoformat()
    try:
        with db.cursor() as cursor:
            # Get player ID from UID
            cursor.execute("SELECT id FROM players WHERE id = %s OR google_uid = %s", (uid, uid))
            player = cursor.fetchone()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")
            
            player_id = player["id"]
            
            cursor.execute(
                "SELECT is_completed, is_claimed FROM daily_challenges WHERE player_id = %s AND date = %s",
                (player_id, today)
            )
            challenge = cursor.fetchone()
            
            if challenge:
                return {"status": "success", "data": {
                    "is_completed": bool(challenge["is_completed"]),
                    "is_claimed": bool(challenge["is_claimed"]),
                    "date": today
                }}
            else:
                return {"status": "success", "data": {
                    "is_completed": False,
                    "is_claimed": False,
                    "date": today
                }}
    finally:
        db.close()

