from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


@router.get("/")
def get_users():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, display_name, username, email, account_type, status, created_at "
                "FROM players ORDER BY created_at DESC"
            )
            return cursor.fetchall()
    finally:
        db.close()


@router.get("/{user_id}")
def get_user(user_id: int):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, display_name, username, email, account_type, status, created_at "
                "FROM players WHERE id=%s", (user_id,)
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            return user
    finally:
        db.close()


class UserUpdate(BaseModel):
    display_name: str
    username: str
    email: Optional[str] = ""
    status: Optional[str] = "Active"


@router.put("/{user_id}")
def update_user(user_id: int, body: UserUpdate):
    status = body.status if body.status in ["Active", "Inactive", "Banned"] else "Active"
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE players SET display_name=%s, username=%s, email=%s, status=%s WHERE id=%s",
                (body.display_name, body.username, body.email, status, user_id)
            )
            db.commit()
            return {"success": True}
    finally:
        db.close()


@router.delete("/{user_id}")
def delete_user(user_id: int):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM players WHERE id=%s", (user_id,))
            db.commit()
            return {"success": True}
    finally:
        db.close()


@router.get("/trophies/{uid}")
def get_trophies(uid: str):
    """Return the current trophy count for a player."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            # uid could be numeric ID (int) or google_uid (string)
            cursor.execute(
                "SELECT trophies FROM players WHERE id=%s OR google_uid=%s", (uid, uid)
            )
            row = cursor.fetchone()
            if not row:
                return {"trophies": 0}
            return {"trophies": row["trophies"]}
    finally:
        db.close()


class FCMTokenUpdate(BaseModel):
    uid: str
    fcm_token: str


@router.post("/fcm-token")
def update_fcm_token(body: FCMTokenUpdate):
    """Save the Firebase Cloud Messaging token for a player."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE players SET fcm_token=%s WHERE id=%s OR google_uid=%s",
                (body.fcm_token, body.uid, body.uid)
            )
            db.commit()
            return {"success": True}
    finally:
        db.close()

