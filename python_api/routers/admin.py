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
    """Send FCM push notifications for a new announcement. Never raises — failures are logged only."""
    success_count = 0
    failure_count = 0

    print(f"\n--- Sending Push Notification for Announcement {announcement_id} ---")
    print(f"Title: {title}")
    print(f"Reward: {reward_amount} {reward_type}")

    # Guard: Firebase must be initialized before attempting to send
    if not firebase_admin._apps:
        print("Firebase Admin is not initialized. Skipping push notifications.")
        print("-----------------------------------------------------------\n")
        return 0, 0

    try:
        cursor.execute("SELECT id, fcm_token FROM players WHERE fcm_token IS NOT NULL AND fcm_token != ''")
        players = cursor.fetchall()
        tokens = [p['fcm_token'] for p in players]

        print(f"Found {len(tokens)} valid FCM tokens.")

        if not tokens:
            print("No FCM tokens found. Skipping push.")
            print("-----------------------------------------------------------\n")
            return 0, 0

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
                    print(f"  Failed token[{idx}]: {resp.exception}")
                    if resp.exception and getattr(resp.exception, 'code', None) in [
                        'messaging/invalid-registration-token',
                        'messaging/registration-token-not-registered'
                    ]:
                        invalid_tokens.append(tokens[idx])

            if invalid_tokens:
                print(f"Removing {len(invalid_tokens)} invalid tokens from database.")
                format_strings = ','.join(['%s'] * len(invalid_tokens))
                cursor.execute(
                    f"UPDATE players SET fcm_token = NULL WHERE fcm_token IN ({format_strings})",
                    tuple(invalid_tokens)
                )

    except Exception as e:
        print(f"Firebase push error (non-fatal): {str(e)}")

    print("-----------------------------------------------------------\n")
    return success_count, failure_count

@router.post("/reward-announcements")
def create_announcement(req: AnnouncementCreateRequest, admin_id: int = Depends(get_current_admin)):
    # Validate reward_type
    if req.reward_type not in ['stars', 'trophies']:
        raise HTTPException(status_code=400, detail="Reward type must be 'stars' or 'trophies'")
    # Validate reward_amount
    if req.reward_amount <= 0:
        raise HTTPException(status_code=400, detail="Reward amount must be greater than 0")
    if req.reward_amount > 10000:
        raise HTTPException(status_code=400, detail="Reward amount must not exceed 10000")
    # Validate title and task_description
    if not req.title or not req.title.strip():
        raise HTTPException(status_code=400, detail="Title must not be empty")
    if not req.task_description or not req.task_description.strip():
        raise HTTPException(status_code=400, detail="Task description must not be empty")
    # Validate date range
    try:
        import datetime as dt
        start = dt.datetime.fromisoformat(req.start_date.replace("Z", "+00:00"))
        end = dt.datetime.fromisoformat(req.end_date.replace("Z", "+00:00"))
        if end <= start:
            raise HTTPException(status_code=400, detail="end_date must be after start_date")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format for start_date or end_date")

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO reward_announcements 
                (title, task_description, reward_type, reward_amount, difficulty_target, theme_target, 
                 start_date, end_date, notification_message, created_by_admin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (req.title.strip(), req.task_description.strip(), req.reward_type, req.reward_amount,
                  req.difficulty_target, req.theme_target, req.start_date, req.end_date,
                  req.notification_message, admin_id))

            announcement_id = cursor.lastrowid

            # Commit the announcement first so it's saved even if push fails
            db.commit()

            # Send push notifications (non-breaking — errors are logged, not raised)
            success_count, failure_count = send_announcement_push(
                cursor, announcement_id, req.title, req.notification_message, req.reward_type, req.reward_amount
            )
            # Commit any token cleanup done during push
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
# LEADERBOARD
# ---------------------------------------------------------
@router.get("/leaderboard")
def get_leaderboard(admin_id: int = Depends(get_current_admin)):
    """Return the top 50 scores with player info for the admin leaderboard tab."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT s.id, s.score, s.stage, s.theme, s.time_seconds, s.achieved_at,
                           p.id as player_id, p.display_name, p.username, p.email,
                           p.account_type, p.stars, p.trophies
                    FROM scores s
                    JOIN players p ON s.player_id = p.id
                    ORDER BY s.score DESC
                    LIMIT 50
                """)
                leaderboard = cursor.fetchall()
            except Exception as e:
                print(f"[Admin] Leaderboard query error: {e}")
                leaderboard = []

            return {"leaderboard": leaderboard}
    finally:
        db.close()

# ---------------------------------------------------------
# PHASE 3: ANALYTICS & MONITORING ENDPOINTS
# ---------------------------------------------------------
@router.get("/analytics/overview")
def get_analytics_overview(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            stats = {
                'total_players': 0, 'active_players': 0, 'total_games': 0,
                'highest_score': 0, 'total_stars': 0, 'total_trophies': 0,
                'total_daily_challenges': 0, 'total_reward_chests': 0,
                'total_bonus_claims': 0, 'total_multiplayer_matches': 0,
                'active_multiplayer_matches': 0, 'tokens_active': 0, 'tokens_inactive': 0,
            }
            try:
                cursor.execute("SELECT COUNT(*) as c FROM players")
                stats['total_players'] = cursor.fetchone()['c']
            except Exception as e:
                print(f"[Analytics] players count error: {e}")

            try:
                cursor.execute("SELECT COUNT(*) as c FROM players WHERE last_login >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
                stats['active_players'] = cursor.fetchone()['c']
            except Exception as e:
                print(f"[Analytics] active_players error: {e}")

            try:
                cursor.execute("SELECT COUNT(*) as c FROM scores")
                stats['total_games'] = cursor.fetchone()['c']
                cursor.execute("SELECT MAX(score) as m FROM scores")
                row = cursor.fetchone()
                stats['highest_score'] = row['m'] or 0 if row else 0
            except Exception as e:
                print(f"[Analytics] scores error: {e}")

            try:
                cursor.execute("SELECT SUM(stars) as s, SUM(trophies) as t FROM players")
                row = cursor.fetchone()
                stats['total_stars'] = int(row['s'] or 0) if row else 0
                stats['total_trophies'] = int(row['t'] or 0) if row else 0
            except Exception as e:
                print(f"[Analytics] stars/trophies error: {e}")

            try:
                cursor.execute("SELECT COUNT(*) as c FROM daily_challenges WHERE is_completed = 1")
                stats['total_daily_challenges'] = cursor.fetchone()['c']
            except Exception as e:
                print(f"[Analytics] daily_challenges error: {e}")

            try:
                cursor.execute("SELECT COUNT(*) as c FROM rewards WHERE reward_status = 'claimed'")
                stats['total_reward_chests'] = cursor.fetchone()['c']
            except Exception as e:
                print(f"[Analytics] rewards error: {e}")

            try:
                cursor.execute("SELECT COUNT(*) as c FROM reward_announcement_claims WHERE is_claimed = 1")
                stats['total_bonus_claims'] = cursor.fetchone()['c']
            except Exception as e:
                print(f"[Analytics] bonus_claims error: {e}")

            try:
                cursor.execute("SELECT COUNT(*) as c FROM multiplayer_matches")
                stats['total_multiplayer_matches'] = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM multiplayer_matches WHERE status = 'active'")
                stats['active_multiplayer_matches'] = cursor.fetchone()['c']
            except Exception as e:
                print(f"[Analytics] multiplayer error: {e}")

            try:
                cursor.execute("SELECT COUNT(*) as c FROM players WHERE fcm_token IS NOT NULL AND fcm_token != ''")
                stats['tokens_active'] = cursor.fetchone()['c']
                cursor.execute("SELECT COUNT(*) as c FROM players WHERE fcm_token IS NULL OR fcm_token = ''")
                stats['tokens_inactive'] = cursor.fetchone()['c']
            except Exception as e:
                print(f"[Analytics] fcm_token error: {e}")

            return stats
    finally:
        db.close()

@router.get("/analytics/players-per-day")
def get_players_per_day(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count 
                    FROM players 
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(created_at) 
                    ORDER BY date ASC
                """)
                return cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] players-per-day error: {e}")
                return []
    finally:
        db.close()

@router.get("/analytics/games-per-day")
def get_games_per_day(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT DATE(achieved_at) as date, COUNT(*) as count 
                    FROM scores 
                    WHERE achieved_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(achieved_at) 
                    ORDER BY date ASC
                """)
                return cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] games-per-day error: {e}")
                return []
    finally:
        db.close()

@router.get("/analytics/daily-challenges")
def get_daily_challenges_analytics(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT date, COUNT(*) as count 
                    FROM daily_challenges 
                    WHERE is_completed = 1 AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    GROUP BY date 
                    ORDER BY date ASC
                """)
                return cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] daily-challenges error: {e}")
                return []
    finally:
        db.close()

@router.get("/analytics/reward-claims")
def get_reward_claims_analytics(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            chests, daily, bonus = [], [], []
            try:
                cursor.execute("""
                    SELECT DATE(claimed_at) as date, COUNT(*) as count 
                    FROM rewards 
                    WHERE reward_status = 'claimed' AND claimed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(claimed_at) 
                    ORDER BY date ASC
                """)
                chests = cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] reward-claims chests error: {e}")

            try:
                cursor.execute("""
                    SELECT DATE(claimed_at) as date, COUNT(*) as count 
                    FROM daily_challenges 
                    WHERE is_claimed = 1 AND claimed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(claimed_at) 
                    ORDER BY date ASC
                """)
                daily = cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] reward-claims daily error: {e}")

            try:
                cursor.execute("""
                    SELECT DATE(claimed_at) as date, COUNT(*) as count 
                    FROM reward_announcement_claims 
                    WHERE is_claimed = 1 AND claimed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(claimed_at) 
                    ORDER BY date ASC
                """)
                bonus = cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] reward-claims bonus error: {e}")

            return {"chests": chests, "daily": daily, "bonus": bonus}
    finally:
        db.close()

@router.get("/analytics/stars-earned")
def get_stars_earned(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT DATE(created_at) as date, SUM(amount) as total
                    FROM admin_reward_logs
                    WHERE reward_type = 'stars' AND action = 'add' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                """)
                return cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] stars-earned error: {e}")
                return []
    finally:
        db.close()

@router.get("/analytics/trophies-earned")
def get_trophies_earned(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT DATE(created_at) as date, SUM(amount) as total
                    FROM admin_reward_logs
                    WHERE reward_type = 'trophies' AND action = 'add' AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                """)
                return cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] trophies-earned error: {e}")
                return []
    finally:
        db.close()

@router.get("/analytics/difficulty-usage")
def get_difficulty_usage(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("SELECT stage, COUNT(*) as count FROM scores GROUP BY stage")
                return cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] difficulty-usage error: {e}")
                return []
    finally:
        db.close()

@router.get("/analytics/theme-usage")
def get_theme_usage(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("SELECT theme, COUNT(*) as count FROM scores GROUP BY theme")
                return cursor.fetchall()
            except Exception as e:
                print(f"[Analytics] theme-usage error: {e}")
                return []
    finally:
        db.close()

@router.get("/analytics/multiplayer")
def get_multiplayer_analytics(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT DATE(started_at) as date, COUNT(*) as count 
                    FROM multiplayer_matches 
                    WHERE started_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(started_at) 
                    ORDER BY date ASC
                """)
                return cursor.fetchall()
            except Exception:
                return []
    finally:
        db.close()

@router.get("/recent-activity")
def get_recent_activity(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT a.id, a.action_type, a.details, a.created_at, p.display_name as player_name 
                FROM activities a 
                LEFT JOIN players p ON a.player_id = p.id 
                ORDER BY a.created_at DESC 
                LIMIT 100
            """)
            return cursor.fetchall()
    finally:
        db.close()

@router.get("/multiplayer-matches")
def get_multiplayer_matches(admin_id: int = Depends(get_current_admin)):
    db = get_db()
    try:
        with db.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT m.*, p1.display_name as p1_name, p2.display_name as p2_name, w.display_name as winner_name
                    FROM multiplayer_matches m
                    LEFT JOIN players p1 ON m.player_1_id = p1.id
                    LEFT JOIN players p2 ON m.player_2_id = p2.id
                    LEFT JOIN players w ON m.winner_id = w.id
                    ORDER BY m.created_at DESC
                    LIMIT 100
                """)
                return cursor.fetchall()
            except Exception:
                return []
    finally:
        db.close()
