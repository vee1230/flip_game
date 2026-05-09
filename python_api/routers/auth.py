from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import os
import hashlib
import httpx
import urllib.parse
from database import get_db
from utils.mailer import send_welcome_email

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    display_name: str
    password: str
    email: Optional[str] = ""
    google_uid: Optional[str] = None
    avatar: Optional[str] = None

class TestEmailRequest(BaseModel):
    email: str


class LoginRequest(BaseModel):
    identifier: str   # username OR email
    password: str


class FirebaseSyncRequest(BaseModel):
    uid: str
    email: str
    name: str
    avatar: Optional[str] = None


def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


@router.post("/register")
def register(req: RegisterRequest):
    if not req.username or not req.display_name or not req.password:
        raise HTTPException(status_code=400, detail="Missing required fields.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    db = get_db()
    try:
        with db.cursor() as cursor:
            # Check if user already exists
            cursor.execute("SELECT id, password_hash, google_uid FROM players WHERE username=%s OR email=%s", (req.username, req.email))
            existing = cursor.fetchone()
            
            hashed = hash_password(req.password)
            account_type = "google" if req.google_uid else "registered"

            email_sent_status = False

            if existing:
                # If they have a password already, it's a conflict
                if existing.get("password_hash"):
                    raise HTTPException(status_code=409, detail="Username or email already taken.")
                
                # If they are a Google user without a password, update them (finalize registration)
                cursor.execute(
                    """UPDATE players 
                       SET display_name=%s, username=%s, password_hash=%s, account_type=%s, google_uid=%s, profile_picture=%s
                       WHERE id=%s""",
                    (req.display_name, req.username, hashed, account_type, req.google_uid or existing.get("google_uid"), req.avatar, existing["id"])
                )
                new_id = existing["id"]
                
                # Send welcome email for Google-linked users who just finalized their account
                if req.email:
                    email_sent_status = send_welcome_email(req.email, req.display_name)
            else:
                # Normal new registration
                cursor.execute(
                    """INSERT INTO players
                       (display_name, username, email, password_hash, account_type, status, google_uid, profile_picture, stars)
                       VALUES (%s, %s, %s, %s, %s, 'Active', %s, %s, 0)""",
                    (req.display_name, req.username, req.email, hashed,
                     account_type, req.google_uid, req.avatar)
                )
                new_id = cursor.lastrowid
                
                # Create a pending welcome reward for the new user
                cursor.execute(
                    """INSERT INTO rewards 
                       (player_id, reward_type, reward_amount, reward_status, source)
                       VALUES (%s, 'welcome_bonus', 50, 'pending', 'manual_signup')""",
                    (new_id,)
                )
                
                # Send welcome email
                if req.email:
                    email_sent_status = send_welcome_email(req.email, req.display_name)

            db.commit()
            
            msg = "Account created successfully" if email_sent_status else "Account created successfully, but email could not be sent"
            
            return {
                "success": True,
                "message": msg,
                "email_sent": email_sent_status,
                "user": {
                    "id":       new_id,
                    "username": req.username,
                    "name":     req.display_name,
                    "email":    req.email,
                    "type":     account_type,
                    "avatar":   req.avatar,
                    "trophies": 0,
                    "stars":    0
                }
            }
    finally:
        db.close()

@router.post("/test-email")
def test_email(req: TestEmailRequest):
    """Temporary endpoint to verify SMTP configuration"""
    success = send_welcome_email(req.email, "Test User")
    if success:
        return {"success": True, "message": f"Test email sent to {req.email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check backend logs and SMTP environment variables.")


@router.post("/login")
def login(req: LoginRequest):
    if not req.identifier or not req.password:
        raise HTTPException(status_code=400, detail="Enter email/username and password.")

    hashed = hash_password(req.password)
    identifier = req.identifier.lower().strip()

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players WHERE LOWER(username)=%s OR LOWER(email)=%s",
                (identifier, identifier)
            )
            user = cursor.fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Invalid email/username or password.")
            if user.get("password_hash") != hashed:
                raise HTTPException(status_code=401, detail="Invalid email/username or password.")

            cursor.execute("UPDATE players SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user["id"],))
            db.commit()

            return {
                "success": True,
                "user": {
                    "id":       user["id"],
                    "username": user["username"],
                    "name":     user["display_name"],
                    "email":    user.get("email", ""),
                    "type":     user["account_type"],
                    "avatar":   user.get("profile_picture"),
                    "trophies": user.get("trophies", 0),
                    "stars":    user.get("stars", 0)
                }
            }
    finally:
        db.close()


@router.post("/logout")
def logout(body: dict = {}):
    """Client-side logout. Optionally revokes Google OAuth token."""
    google_token = body.get("google_token")
    if google_token:
        try:
            httpx.get(f"https://oauth2.googleapis.com/revoke?token={google_token}")
        except Exception:
            pass
    return {"status": "ok", "message": "Logged out successfully."}


@router.get("/google/login")
def google_login():
    """Redirects the user to Google's OAuth 2.0 consent screen."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "online",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(code: Optional[str] = None, error: Optional[str] = None):
    """Handles Google OAuth callback, token exchange, and user creation."""
    redirect_url = "http://localhost/match-game/index.html"
    
    if error:
        return RedirectResponse(f"{redirect_url}?login=failed&reason={error}")
        
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
        
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    try:
        token_resp = httpx.post(token_url, data=token_data)
        token_json = token_resp.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Error connecting to Google token endpoint")

    if "error" in token_json or "access_token" not in token_json:
        err = token_json.get("error_description", "Unknown error")
        raise HTTPException(status_code=400, detail=f"Error fetching access token: {err}")

    access_token = token_json["access_token"]

    profile_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        profile_resp = httpx.get(profile_url, headers=headers)
        profile_json = profile_resp.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Error fetching Google profile")

    if "id" not in profile_json:
        raise HTTPException(status_code=400, detail="Error fetching user profile ID")

    google_id = profile_json["id"]
    name = profile_json.get("name", "User")
    email = profile_json.get("email", "")
    avatar = profile_json.get("picture", "")

    if not email:
        raise HTTPException(status_code=400, detail="Error: Email is required.")

    db = get_db()
    redirect_url = "http://localhost/match-game/index.html"
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM players WHERE google_uid = %s OR email = %s", (google_id, email))
            existing_user = cursor.fetchone()

            if existing_user:
                params = {
                    "login": "success",
                    "uid": existing_user["id"],
                    "name": existing_user["display_name"],
                    "avatar": existing_user["profile_picture"] or avatar,
                    "email": email,
                    "trophies": existing_user.get("trophies", 0),
                    "stars": existing_user.get("stars", 0)
                }
            else:
                # Use email as default username for Google auth
                username = email.split("@")[0] if "@" in email else email
                cursor.execute(
                    """INSERT INTO players 
                       (display_name, username, email, account_type, status, google_uid, profile_picture, trophies, stars) 
                       VALUES (%s, %s, %s, 'Google', 'Active', %s, %s, 0, 0)""",
                    (name, username, email, google_id, avatar)
                )
                db.commit()
                new_id = cursor.lastrowid

                # Create a pending welcome reward (50 trophies to be claimed manually)
                cursor.execute(
                    """INSERT INTO rewards 
                       (player_id, reward_type, reward_amount, reward_status, source)
                       VALUES (%s, 'welcome_bonus', 50, 'pending', 'google_signup')""",
                    (new_id,)
                )
                db.commit()
                
                # Send welcome email on new registration
                send_welcome_email(email, name)
                
                params = {
                    "msg": "registered",
                    "uid": new_id,
                    "name": name,
                    "avatar": avatar,
                    "email": email,
                    "trophies": 0,
                    "stars": 0,
                    "has_pending_reward": True
                }
                
            redirect_qs = urllib.parse.urlencode(params)
            return RedirectResponse(f"{redirect_url}?{redirect_qs}")
    finally:
        db.close()


@router.post("/firebase/sync")
def firebase_sync(req: FirebaseSyncRequest):
    """Syncs a Firebase Auth user with the MySQL players table."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Check if player exists by google_uid (firebase uid) or email
            cursor.execute("SELECT * FROM players WHERE google_uid = %s OR email = %s", (req.uid, req.email))
            user = cursor.fetchone()

            if user:
                # Update existing user
                cursor.execute(
                    "UPDATE players SET display_name=%s, profile_picture=%s, google_uid=%s WHERE id=%s",
                    (req.name, req.avatar or user.get("profile_picture"), req.uid, user["id"])
                )
                db.commit()
                user_id = user["id"]
                trophies = user.get("trophies", 0)
                stars = user.get("stars", 0)
                username = user["username"]
            else:
                # Create new user
                username = req.email.split("@")[0] if "@" in req.email else req.uid[:10]
                cursor.execute(
                    """INSERT INTO players 
                       (display_name, username, email, account_type, status, google_uid, profile_picture, trophies, stars) 
                       VALUES (%s, %s, %s, 'Google', 'Active', %s, %s, 0, 0)""",
                    (req.name, username, req.email, req.uid, req.avatar)
                )
                db.commit()
                user_id = cursor.lastrowid
                trophies = 0
                stars = 0
                
                # Create a pending welcome reward for the new user
                cursor.execute(
                    """INSERT INTO rewards 
                       (player_id, reward_type, reward_amount, reward_status, source)
                       VALUES (%s, 'welcome_bonus', 50, 'pending', 'google_signup')""",
                    (user_id,)
                )
                db.commit()
                
                # Send welcome email on new registration via Firebase
                if req.email:
                    try:
                        email_sent = send_welcome_email(req.email, req.name)
                        if email_sent:
                            print(f"[Auth] Welcome email sent successfully to {req.email}")
                        else:
                            print(f"[Auth] Welcome email FAILED for {req.email} (returned False)")
                    except Exception as e:
                        print(f"[Auth] Exception sending welcome email to {req.email}: {e}")
            
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username,
                    "name": req.name,
                    "email": req.email,
                    "type": "google",
                    "avatar": req.avatar,
                    "trophies": trophies,
                    "stars": stars
                }
            }
    finally:
        db.close()
