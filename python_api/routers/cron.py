from fastapi import APIRouter
from firebase_admin import messaging
from database import get_db

router = APIRouter()

@router.post("/daily-reward-push")
def send_daily_reward_push():
    """
    Sends a push notification to all users who have an FCM token.
    This endpoint should be triggered daily via a cron job.
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Fetch all users with a registered FCM token
            cursor.execute("SELECT fcm_token FROM players WHERE fcm_token IS NOT NULL AND fcm_token != ''")
            tokens = [row['fcm_token'] for row in cursor.fetchall()]
    finally:
        db.close()

    if not tokens:
        return {"status": "success", "message": "No tokens found. Sent 0 notifications."}

    # Prepare the message
    # We use MulticastMessage to send to multiple tokens efficiently.
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title="⭐ Daily Challenge Ready!",
            body="Play Easy Mode now and match 3 pairs to claim your 50 Stars!"
        ),
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message)
        return {
            "status": "success", 
            "success_count": response.success_count,
            "failure_count": response.failure_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
