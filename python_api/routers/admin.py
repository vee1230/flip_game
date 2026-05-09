from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import jwt
import datetime
import os
import firebase_admin
from firebase_admin import messaging

from database import get_db

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-admin-key-flip-game-123")
JWT_ALGORITHM = "HS256"

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class RewardAdjustRequest(BaseModel):
    player_id: int
    type: str  # stars or trophies
    action: str  # add or deduct
    amount: int
    reason: str

class AnnouncementCreateRequest(BaseModel):
    title: str
    task_description: str
    reward_type: str  # stars or trophies
    reward_amount: int
    difficulty_target: str = "Any"
    theme_target: str = "Any"
    start_date: str
    end_date: str
    notification_message: str

class AnnouncementUpdateRequest(BaseModel):
    title: Optional[str] = None
    task_description: Optional[str] = None
    reward_type: Optional[str] = None
    reward_amount: Optional[int] = None
    difficulty_target: Optional[str] = None
    theme_target: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notification_message: Optional[str] = None

class AnnouncementStatusRequest(BaseModel):
    status: str  # active or inactive

# ---------------------------------------------------------
# AUTHENTICATION & DEPENDENCY
# ---------------------------------------------------------
def get_current_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["admin_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/login")
def admin_login(req: AdminLoginRequest):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM admins WHERE username = %s", (req.username,))
            admin = cursor.fetchone()
            if not admin:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Verify password
            import bcrypt
            try:
                # Check bcrypt hash
                if not bcrypt.checkpw(req.password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                    raise HTTPException(status_code=401, detail="Invalid credentials")
            except Exception:
                # Fallback to sha256 if someone manually inserted it or bcrypt isn't available
                import hashlib
                if hashlib.sha256(req.password.encode()).hexdigest() != admin['password_hash']:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Generate JWT token
            token = jwt.encode({
                "admin_id": admin["id"],
                "username": admin["username"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, JWT_SECRET, algorithm=JWT_ALGORITHM)
            
            return {
                "success": True,
                "token": token,
                "admin": {
                    "id": admin["id"],
                    "username": admin["username"],
                    "name": admin["display_name"]
                }
            }
    finally:
        db.close()

# ---------------------------------------------------------
# DASHBOARD OVERVIEW
# ---------------------------------------------------------
@router.get("/overview")
def get_overview(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM players")
            total_players = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as active FROM players WHERE last_login >= NOW() - INTERVAL 7 DAY")
            active_players = cursor.fetchone()['active']

            cursor.execute("SELECT COUNT(*) as total FROM scores")
            total_games = cursor.fetchone()['total']

            cursor.execute("SELECT MAX(score) as max_score FROM scores")
            max_score_row = cursor.fetchone()
            max_score = max_score_row['max_score'] if max_score_row and max_score_row['max_score'] is not None else 0

            cursor.execute("SELECT SUM(stars) as total FROM players")
            total_stars = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT SUM(trophies) as total FROM players")
            total_trophies = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT COUNT(*) as total FROM daily_challenges WHERE is_completed = 1")
            total_daily_challenges = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT COUNT(*) as total FROM multiplayer_matches")
            total_multiplayer = cursor.fetchone()['total'] or 0

            return {
                'total_players': total_players,
                'active_players': active_players,
                'total_games': total_games,
                'max_score': max_score,
                'total_stars': int(total_stars),
                'total_trophies': int(total_trophies),
                'total_daily_challenges': total_daily_challenges,
                'total_multiplayer': total_multiplayer
            }
    finally:
        db.close()

# ---------------------------------------------------------
# PLAYER MANAGEMENT
# ---------------------------------------------------------
@router.get("/players")
def get_players(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.display_name, p.username, p.email, p.account_type, p.status, 
                       p.stars, p.trophies, p.last_login, p.created_at,
                       (SELECT MAX(score) FROM scores WHERE player_id = p.id) as best_score,
                       (SELECT COUNT(*) FROM scores WHERE player_id = p.id) as games_played
                FROM players p 
                ORDER BY p.created_at DESC
            """)
            return cursor.fetchall()
    finally:
        db.close()

# ---------------------------------------------------------
# REWARD MANAGEMENT
# ---------------------------------------------------------
@router.post("/rewards/adjust")
def adjust_reward(req: RewardAdjustRequest, admin_id: int = Depends(get_current_admin)):
    if req.type not in ['stars', 'trophies']:
        raise HTTPException(status_code=400, detail="Invalid reward type")
    if req.action not in ['add', 'deduct']:
        raise HTTPException(status_code=400, detail="Invalid action")
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM players WHERE id = %s", (req.player_id,))
            player = cursor.fetchone()
            if not player:
                raise HTTPException(status_code=404, detail="Player not found")
            
            previous_balance = player[req.type]
            
            if req.action == 'add':
                new_balance = previous_balance + req.amount
            else:
                new_balance = previous_balance - req.amount
                if new_balance < 0:
                    raise HTTPException(status_code=400, detail=f"Insufficient {req.type}")
            
            # Update player balance
            cursor.execute(f"UPDATE players SET {req.type} = %s WHERE id = %s", (new_balance, req.player_id))
            
            # Log the adjustment
            cursor.execute("""
                INSERT INTO admin_reward_logs 
                (admin_id, player_id, reward_type, action, amount, previous_balance, new_balance, reason) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (admin_id, req.player_id, req.type, req.action, req.amount, previous_balance, new_balance, req.reason))
            
            # Add to activities log as well
            action_text = f"Admin {'added' if req.action == 'add' else 'deducted'} {req.amount} {req.type}"
            cursor.execute("INSERT INTO activities (player_id, action_type, details) VALUES (%s, %s, %s)", 
                           (req.player_id, 'admin_reward_adjustment', f"{action_text}. Reason: {req.reason}"))
            
            db.commit()
            
            return {
                "success": True, 
                "message": f"Successfully updated player {req.type}", 
                "new_balance": new_balance
            }
    finally:
        db.close()

@router.get("/reward-logs")
def get_reward_logs(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT l.*, a.display_name as admin_name, p.display_name as player_name, p.username as player_username
                FROM admin_reward_logs l
                JOIN admins a ON l.admin_id = a.id
                JOIN players p ON l.player_id = p.id
                ORDER BY l.created_at DESC
                LIMIT 100
            """)
            return cursor.fetchall()
    finally:
        db.close()

# ---------------------------------------------------------
# REWARD ANNOUNCEMENTS
# ---------------------------------------------------------

def send_announcement_push(cursor, announcement_id, title, notification_message, reward_type, reward_amount):
    cursor.execute("SELECT id, fcm_token FROM players WHERE fcm_token IS NOT NULL AND fcm_token != ''")
    players = cursor.fetchall()
    tokens = [p['fcm_token'] for p in players]
    
    success_count = 0
    failure_count = 0
    
    print(f"\n--- Sending Push Notification for Announcement {announcement_id} ---")
    print(f"Title: {title}")
    print(f"Reward: {reward_amount} {reward_type}")
    print(f"Found {len(tokens)} valid FCM tokens.")
    
    if not tokens:
        print("No FCM tokens found. Skipping push.")
        return 0, 0
        
    try:
        title_prefix = "⭐" if reward_type == 'stars' else "🏆"
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=f"{title_prefix} {title}",
                body=notification_message or f"New bonus challenge available! Earn {reward_amount} {reward_type}."
            ),
            tokens=tokens,
        )
        response = messaging.send_multicast(message)
        success_count = response.success_count
        failure_count = response.failure_count
        
        print(f"Push Sent! Success: {success_count}, Failure: {failure_count}")
        
        if failure_count > 0:
            invalid_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    print(f"Failed token at index {idx}: {resp.exception}")
                    if resp.exception and getattr(resp.exception, 'code', None) in ['messaging/invalid-registration-token', 'messaging/registration-token-not-registered']:
                        invalid_tokens.append(tokens[idx])
            
            if invalid_tokens:
                print(f"Removing {len(invalid_tokens)} invalid tokens from database.")
                format_strings = ','.join(['%s'] * len(invalid_tokens))
                cursor.execute(f"UPDATE players SET fcm_token = NULL WHERE fcm_token IN ({format_strings})", tuple(invalid_tokens))
                
    except Exception as e:
        print(f"Firebase Admin Error: {str(e)}")
        
    print("-----------------------------------------------------------\n")
    return success_count, failure_count

@router.post("/reward-announcements")
def create_announcement(req: AnnouncementCreateRequest, admin_id: int = Depends(get_current_admin)):
    if req.reward_amount <= 0:
        raise HTTPException(status_code=400, detail="Reward amount must be greater than 0")
    if req.reward_type not in ['stars', 'trophies']:
        raise HTTPException(status_code=400, detail="Reward type must be stars or trophies")

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO reward_announcements 
                (title, task_description, reward_type, reward_amount, difficulty_target, theme_target, 
                 start_date, end_date, notification_message, created_by_admin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (req.title, req.task_description, req.reward_type, req.reward_amount, req.difficulty_target, 
                  req.theme_target, req.start_date, req.end_date, req.notification_message, admin_id))
            
            announcement_id = cursor.lastrowid
            
            # Send push notifications
            success_count, failure_count = send_announcement_push(
                cursor, announcement_id, req.title, req.notification_message, req.reward_type, req.reward_amount
            )
                    
            db.commit()
            return {
                "success": True, 
                "id": announcement_id, 
                "notification_success_count": success_count,
                "notification_failure_count": failure_count
            }
    finally:
        db.close()

@router.get("/reward-announcements")
def get_announcements(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT a.*, ad.display_name as admin_name,
                (SELECT COUNT(*) FROM reward_announcement_claims WHERE announcement_id = a.id AND is_claimed = 1) as total_claims
                FROM reward_announcements a
                LEFT JOIN admins ad ON a.created_by_admin = ad.id
                ORDER BY a.created_at DESC
            """)
            return cursor.fetchall()
    finally:
        db.close()

@router.put("/reward-announcements/{announcement_id}")
def update_announcement(announcement_id: int, req: AnnouncementUpdateRequest, admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Build dynamic update query
            updates = []
            params = []
            
            for field, value in req.model_dump(exclude_unset=True).items():
                if field == 'reward_amount' and value <= 0:
                    raise HTTPException(status_code=400, detail="Reward amount must be greater than 0")
                if field == 'reward_type' and value not in ['stars', 'trophies']:
                    raise HTTPException(status_code=400, detail="Reward type must be stars or trophies")
                    
                updates.append(f"{field} = %s")
                params.append(value)
                
            if not updates:
                return {"success": True, "message": "Nothing to update"}
                
            query = f"UPDATE reward_announcements SET {', '.join(updates)} WHERE id = %s"
            params.append(announcement_id)
            
            cursor.execute(query, tuple(params))
            db.commit()
            
            return {"success": True}
    finally:
        db.close()

@router.patch("/reward-announcements/{announcement_id}/status")
def toggle_announcement_status(announcement_id: int, req: AnnouncementStatusRequest, admin_id: int = Depends(get_current_admin)):
    if req.status not in ['active', 'inactive']:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("UPDATE reward_announcements SET status = %s WHERE id = %s", (req.status, announcement_id))
            db.commit()
            return {"success": True}
    finally:
        db.close()

@router.post("/reward-announcements/{announcement_id}/notify")
def notify_announcement(announcement_id: int, admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM reward_announcements WHERE id = %s", (announcement_id,))
            ann = cursor.fetchone()
            if not ann:
                raise HTTPException(status_code=404, detail="Announcement not found")
                
            success_count, failure_count = send_announcement_push(
                cursor, announcement_id, ann['title'], ann['notification_message'], ann['reward_type'], ann['reward_amount']
            )
            
            db.commit()
            return {
                "success": True, 
                "notification_success_count": success_count,
                "notification_failure_count": failure_count
            }
    finally:
        db.close()

# ---------------------------------------------------------
# EXISTING ENDPOINTS MOVED BEHIND JWT AUTH
# ---------------------------------------------------------
@router.get("/activities")
def get_activities(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT a.action_type, a.details, a.created_at, p.display_name 
                FROM activities a 
                JOIN players p ON a.player_id = p.id 
                ORDER BY a.created_at DESC 
                LIMIT 100
            """)
            return cursor.fetchall()
    finally:
        db.close()

@router.get("/leaderboard")
def get_leaderboard(admin_id: int = Depends(get_current_admin), limit: int = 100, stage: str = None, theme: str = None):
    # Same implementation as before, just protected with admin auth
    db = get_db()
    try:
        with db.cursor() as cursor:
            where_clause = "WHERE 1=1"
            params = []
            if stage:
                where_clause += " AND s.stage = %s"
                params.append(stage)
            if theme:
                where_clause += " AND s.theme = %s"
                params.append(theme)
            
            query = f"""
                SELECT p.id as player_id, p.display_name, p.account_type, s.score, s.stage, s.theme,
                       s.time_seconds, s.moves, s.achieved_at,
                       ROW_NUMBER() OVER (ORDER BY s.score DESC, s.time_seconds ASC) as rank
                FROM scores s JOIN players p ON s.player_id = p.id 
                {where_clause} ORDER BY s.score DESC, s.time_seconds ASC LIMIT %s
            """
            params.append(limit)
            cursor.execute(query, params)
            leaderboard_data = cursor.fetchall()
            
            return {'leaderboard': leaderboard_data, 'total_records': len(leaderboard_data)}
    finally:
        db.close()

@router.get("/analytics")
def get_analytics(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT stage, COUNT(*) as count FROM scores GROUP BY stage")
            difficulties = cursor.fetchall()
            cursor.execute("SELECT theme, COUNT(*) as count FROM scores GROUP BY theme")
            themes = cursor.fetchall()
            cursor.execute("SELECT DATE(created_at) as date, COUNT(*) as count FROM players GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 30")
            new_players = cursor.fetchall()
            return {
                'difficulties': difficulties,
                'themes': themes,
                'new_players': new_players
            }
    finally:
        db.close()
