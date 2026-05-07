from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

from database import get_db

router = APIRouter()

@router.get("/overview")
def get_overview():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM players")
            total_users = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM scores")
            total_games = cursor.fetchone()['total']

            cursor.execute("SELECT MAX(score) as max_score FROM scores")
            max_score_row = cursor.fetchone()
            max_score = max_score_row['max_score'] if max_score_row and max_score_row['max_score'] is not None else 0

            cursor.execute("SELECT COUNT(*) as active FROM players WHERE status = 'Active'")
            active_users = cursor.fetchone()['active']

            cursor.execute("SELECT COUNT(*) as total FROM players WHERE account_type = 'Guest'")
            total_guests = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM players WHERE account_type = 'Google'")
            total_google = cursor.fetchone()['total']

            cursor.execute("SELECT SUM(trophies) as total FROM players")
            total_trophies = cursor.fetchone()['total'] or 0

            return {
                'total_users': total_users,
                'total_games': total_games,
                'max_score': max_score,
                'active_users': active_users,
                'total_guests': total_guests,
                'total_google': total_google,
                'total_trophies': total_trophies
            }
    finally:
        db.close()


@router.get("/users")
def get_users():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id, display_name, username, email, account_type, status, trophies, created_at FROM players ORDER BY created_at DESC")
            return cursor.fetchall()
    finally:
        db.close()


@router.get("/leaderboard")
def get_leaderboard(limit: int = 100, stage: str = None, theme: str = None):
    """
    Enhanced leaderboard with proper ranking logic.
    Primary sort: Score (DESC)
    Secondary sort: Time (ASC) - faster times rank higher for same score
    """
    db = get_db()
    try:
        with db.cursor() as cursor:
            # Build dynamic query with optional filters
            where_clause = "WHERE 1=1"
            params = []
            
            if stage:
                where_clause += " AND s.stage = %s"
                params.append(stage)
            
            if theme:
                where_clause += " AND s.theme = %s"
                params.append(theme)
            
            # Main leaderboard query - ranked with tie-breaking
            query = f"""
                SELECT 
                    p.id as player_id,
                    p.display_name,
                    p.account_type,
                    s.score,
                    s.stage,
                    s.theme,
                    s.time_seconds,
                    s.moves,
                    s.achieved_at,
                    ROW_NUMBER() OVER (ORDER BY s.score DESC, s.time_seconds ASC) as rank
                FROM scores s 
                JOIN players p ON s.player_id = p.id 
                {where_clause}
                ORDER BY s.score DESC, s.time_seconds ASC
                LIMIT %s
            """
            params.append(limit)
            
            cursor.execute(query, params)
            leaderboard_data = cursor.fetchall()
            
            # Get summary statistics
            summary_query = f"""
                SELECT 
                    MAX(s.score) as highest_score,
                    MIN(s.time_seconds) as fastest_time,
                    COUNT(DISTINCT s.player_id) as total_players,
                    COUNT(*) as total_games
                FROM scores s
                {where_clause if where_clause != 'WHERE 1=1' else ''}
            """
            summary_params = params[:-1] if limit else params
            cursor.execute(summary_query, summary_params)
            summary = cursor.fetchone()
            
            # Get top player name
            top_player_query = f"""
                SELECT p.display_name
                FROM scores s
                JOIN players p ON s.player_id = p.id
                {where_clause}
                ORDER BY s.score DESC, s.time_seconds ASC
                LIMIT 1
            """
            cursor.execute(top_player_query, params[:-1])
            top_player_row = cursor.fetchone()
            top_player = top_player_row['display_name'] if top_player_row else "N/A"
            
            # Get most played theme
            theme_query = """
                SELECT s.theme, COUNT(*) as count
                FROM scores s
                GROUP BY s.theme
                ORDER BY count DESC
                LIMIT 1
            """
            cursor.execute(theme_query)
            theme_row = cursor.fetchone()
            most_played_theme = theme_row['theme'] if theme_row else "N/A"
            
            return {
                'leaderboard': leaderboard_data,
                'summary': {
                    'highest_score': summary['highest_score'] or 0,
                    'top_player': top_player,
                    'fastest_time': summary['fastest_time'] or 0,
                    'most_played_theme': most_played_theme,
                    'total_players': summary['total_players'] or 0,
                    'total_games': summary['total_games'] or 0
                },
                'total_records': len(leaderboard_data)
            }
    finally:
        db.close()


@router.get("/activities")
def get_activities():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT a.action_type, a.details, a.created_at, p.display_name 
                FROM activities a 
                JOIN players p ON a.player_id = p.id 
                ORDER BY a.created_at DESC 
                LIMIT 15
            """)
            return cursor.fetchall()
    finally:
        db.close()


@router.get("/analytics")
def get_analytics():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT stage, COUNT(*) as count FROM scores GROUP BY stage")
            difficulties = cursor.fetchall()

            cursor.execute("SELECT theme, COUNT(*) as count FROM scores GROUP BY theme")
            themes = cursor.fetchall()

            return {
                'difficulties': difficulties,
                'themes': themes
            }
    finally:
        db.close()

class UserUpdate(BaseModel):
    id: int
    display_name: str
    username: str
    email: str = ""
    status: str = "Active"

@router.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate):
    if user.id != user_id:
        raise HTTPException(status_code=400, detail="ID mismatch")
    
    db = get_db()
    try:
        with db.cursor() as cursor:
            status = user.status if user.status in ['Active', 'Inactive', 'Banned'] else 'Active'
            cursor.execute(
                "UPDATE players SET display_name=%s, username=%s, email=%s, status=%s WHERE id=%s",
                (user.display_name, user.username, user.email, status, user_id)
            )
            db.commit()
            return {"success": True}
    finally:
        db.close()

@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM players WHERE id=%s", (user_id,))
            db.commit()
            return {"success": True}
    finally:
        db.close()

class AnnouncementRequest(BaseModel):
    message: str

@router.post("/announcement")
def send_announcement(req: AnnouncementRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT google_uid FROM players WHERE google_uid IS NOT NULL AND google_uid != ''")
            users = cursor.fetchall()
            for u in users:
                cursor.execute(
                    "INSERT INTO notifications (user_google_id, title, message, type) VALUES (%s, %s, %s, %s)",
                    (u['google_uid'], "System Announcement", req.message, "announcement")
                )
            db.commit()
            return {"success": True, "notified": len(users)}
    finally:
        db.close()

@router.delete("/leaderboard")
def reset_leaderboard():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM scores")
            db.commit()
            return {"success": True}
    finally:
        db.close()

