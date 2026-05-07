from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db

router = APIRouter()


class ClaimRequest(BaseModel):
    player_id: int


@router.get("/pending/{player_id}")
def get_pending_rewards(player_id: int):
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Get pending
            cursor.execute(
                "SELECT id, reward_type, reward_amount, source, created_at FROM rewards WHERE player_id = %s AND reward_status = 'pending'",
                (player_id,)
            )
            pending = cursor.fetchall()

            # Get claimed count
            cursor.execute(
                "SELECT COUNT(*) as count FROM rewards WHERE player_id = %s AND reward_status = 'claimed'",
                (player_id,)
            )
            claimed_count = cursor.fetchone()["count"]

            return {
                "pending": pending,
                "claimed_count": claimed_count,
                "eligible": len(pending) > 0 or claimed_count > 0
            }
    finally:
        db.close()


@router.post("/claim/{reward_id}")
def claim_reward(reward_id: int, req: ClaimRequest):
    """
    Claim a specific reward.
    - Validates the reward belongs to the requesting player.
    - Ensures it hasn't already been claimed (anti-duplicate).
    - Adds the trophy amount to the player's balance atomically.
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Lock the row and verify ownership + status
            cursor.execute(
                """SELECT id, player_id, reward_amount, reward_status
                   FROM rewards
                   WHERE id = %s AND player_id = %s
                   FOR UPDATE""",
                (reward_id, req.player_id)
            )
            reward = cursor.fetchone()

            if not reward:
                raise HTTPException(status_code=404, detail="Reward not found.")

            if reward["reward_status"] == "claimed":
                raise HTTPException(status_code=409, detail="Reward already claimed.")

            amount = reward["reward_amount"]

            # Mark as claimed
            cursor.execute(
                """UPDATE rewards
                   SET reward_status = 'claimed', claimed_at = NOW()
                   WHERE id = %s""",
                (reward_id,)
            )

            # Add trophies to player
            cursor.execute(
                "UPDATE players SET trophies = trophies + %s WHERE id = %s",
                (amount, req.player_id)
            )

            # Fetch new trophy total
            cursor.execute("SELECT trophies FROM players WHERE id = %s", (req.player_id,))
            row = cursor.fetchone()
            new_trophies = row["trophies"] if row else 0

            db.commit()
            return {"success": True, "claimed_amount": amount, "new_trophies": new_trophies}
    finally:
        db.close()
