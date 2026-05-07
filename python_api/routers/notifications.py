from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from database import get_db

router = APIRouter()


@router.get("/{uid}")
def get_notifications(uid: str):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, message, type, created_at FROM notifications "
                "WHERE user_google_id=%s AND is_read=0 ORDER BY created_at DESC",
                (uid,)
            )
            return {"status": "success", "data": cursor.fetchall()}
    finally:
        db.close()


class MarkReadRequest(BaseModel):
    notification_ids: List[int]


@router.post("/mark-read")
def mark_read(req: MarkReadRequest):
    if not req.notification_ids:
        raise HTTPException(status_code=400, detail="Missing notification IDs.")

    db = get_db()
    try:
        with db.cursor() as cursor:
            placeholders = ",".join(["%s"] * len(req.notification_ids))
            cursor.execute(
                f"UPDATE notifications SET is_read=1 WHERE id IN ({placeholders})",
                tuple(req.notification_ids)
            )
            db.commit()
            return {"status": "success"}
    finally:
        db.close()


class NotifyRequest(BaseModel):
    target_uid: str
    title: str
    message: str
    type: str


@router.post("/send")
def send_notification(req: NotifyRequest):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT display_name as name, email FROM players WHERE google_uid=%s", (req.target_uid,)
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="Target user not found.")

            cursor.execute(
                "INSERT INTO notifications (user_google_id, title, message, type) VALUES (%s,%s,%s,%s)",
                (req.target_uid, req.title, req.message, req.type)
            )
            db.commit()
            return {"status": "success", "message": f"Notification saved for {user['email']}"}
    finally:
        db.close()
