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


@router.get("/announcements/active/{player_id}")
def get_active_announcements(player_id: int):
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Get active announcements that haven't expired yet
            cursor.execute("""
                SELECT id, title, task_description, reward_type, reward_amount, 
                       difficulty_target, theme_target, end_date
                FROM reward_announcements
                WHERE status = 'active' AND end_date > NOW()
                ORDER BY created_at DESC
            """)
            announcements = cursor.fetchall()
            
            # For each, check if player has claimed
            result = []
            for ann in announcements:
                cursor.execute("""
                    SELECT is_claimed FROM reward_announcement_claims
                    WHERE announcement_id = %s AND player_id = %s
                """, (ann['id'], player_id))
                claim = cursor.fetchone()
                
                ann['is_claimed'] = claim['is_claimed'] == 1 if claim else False
                result.append(ann)
                
            return result
    finally:
        db.close()


class AnnouncementClaimRequest(BaseModel):
    player_id: int
    completed: bool = False  # Frontend must send completed=True to confirm task is done


@router.post("/announcements/{announcement_id}/claim")
def claim_announcement(announcement_id: int, req: AnnouncementClaimRequest):
    db = get_db()
    try:
        with db.cursor() as cursor:
            # 1. Validate announcement exists and is active
            cursor.execute(
                "SELECT * FROM reward_announcements WHERE id = %s AND status = 'active' AND end_date > NOW()",
                (announcement_id,)
            )
            ann = cursor.fetchone()
            if not ann:
                raise HTTPException(status_code=404, detail="Announcement not found or has expired")

            # 2. Validate reward_type to prevent SQL injection in dynamic UPDATE
            reward_type = ann['reward_type']
            if reward_type not in ('stars', 'trophies'):
                raise HTTPException(status_code=500, detail="Invalid reward type in announcement")

            # 3. Lock the claim row to prevent double-claiming (SELECT ... FOR UPDATE)
            cursor.execute(
                """SELECT * FROM reward_announcement_claims
                   WHERE announcement_id = %s AND player_id = %s
                   FOR UPDATE""",
                (announcement_id, req.player_id)
            )
            existing_claim = cursor.fetchone()

            if existing_claim and existing_claim['is_claimed'] == 1:
                raise HTTPException(status_code=400, detail="Already claimed")

            # 4. Check task completion — require frontend to confirm task is done
            #    If a claim row already exists with is_completed=1, allow it.
            #    Otherwise, the frontend must send completed=True.
            task_completed = (existing_claim and existing_claim['is_completed'] == 1) or req.completed
            if not task_completed:
                raise HTTPException(
                    status_code=400,
                    detail="Task not completed yet. Complete the task before claiming the reward."
                )

            # 5. Upsert the claim record
            if not existing_claim:
                cursor.execute(
                    """INSERT INTO reward_announcement_claims
                       (announcement_id, player_id, is_completed, is_claimed, claimed_at)
                       VALUES (%s, %s, 1, 1, NOW())""",
                    (announcement_id, req.player_id)
                )
            else:
                cursor.execute(
                    """UPDATE reward_announcement_claims
                       SET is_completed = 1, is_claimed = 1, claimed_at = NOW()
                       WHERE announcement_id = %s AND player_id = %s""",
                    (announcement_id, req.player_id)
                )

            # 6. Give reward to player (reward_type already validated above)
            cursor.execute(
                f"UPDATE players SET {reward_type} = {reward_type} + %s WHERE id = %s",
                (ann['reward_amount'], req.player_id)
            )

            # 7. Fetch new balances for consistent response
            cursor.execute("SELECT stars, trophies FROM players WHERE id = %s", (req.player_id,))
            player_row = cursor.fetchone()
            total_stars = player_row['stars'] if player_row else 0
            total_trophies = player_row['trophies'] if player_row else 0

            # 8. Log the activity
            try:
                cursor.execute(
                    "INSERT INTO activities (player_id, action_type, details) VALUES (%s, %s, %s)",
                    (req.player_id, 'bonus_claim',
                     f"Claimed {ann['reward_amount']} {reward_type} from announcement #{announcement_id}: {ann['title']}")
                )
            except Exception as log_err:
                print(f"[Rewards] Activity log error (non-fatal): {log_err}")

            db.commit()

            return {
                "success": True,
                "reward_type": reward_type,
                "amount_claimed": ann['reward_amount'],
                "new_balance": total_stars if reward_type == 'stars' else total_trophies,
                "total_stars": total_stars,
                "total_trophies": total_trophies,
                "message": f"Successfully claimed {ann['reward_amount']} {reward_type}!"
            }
    finally:
        db.close()
