"""
database.py — MySQL connection using PyMySQL
"""
import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

# Load .env from the project root (one level up)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "127.0.0.1"),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", os.getenv("DB_PASS", "")),
    "database": os.getenv("DB_NAME", "memory_match"),
    "cursorclass": pymysql.cursors.DictCursor,
    "charset":  "utf8mb4",
    "connect_timeout": 5,
    "read_timeout": 10,
    "write_timeout": 10,
}


def get_db():
    """Return a new PyMySQL connection (caller must close it)."""
    return pymysql.connect(**DB_CONFIG)

def _safe_alter(cursor, sql):
    """Run an ALTER TABLE statement; silently ignore duplicate-column errors (1060)."""
    try:
        cursor.execute(sql)
    except pymysql.err.OperationalError as e:
        if e.args[0] != 1060:
            raise

def init_db():
    """Run database migrations on startup to ensure all tables and columns exist."""
    try:
        db = get_db()
        with db.cursor() as cursor:
            # 1. Execute the base schema from database.sql
            sql_file_path = os.path.join(os.path.dirname(__file__), "..", "database.sql")
            if os.path.exists(sql_file_path):
                with open(sql_file_path, "r", encoding="utf-8") as f:
                    sql_commands = f.read().split(";")
                    for cmd in sql_commands:
                        if cmd.strip():
                            try:
                                cursor.execute(cmd)
                            except Exception:
                                pass  # Ignore if table/index already exists

            # 2. rewards table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `rewards` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `player_id` int(11) NOT NULL,
              `reward_type` varchar(50) NOT NULL,
              `reward_amount` int(11) NOT NULL,
              `reward_status` varchar(50) DEFAULT 'pending',
              `source` varchar(100) DEFAULT NULL,
              `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
              `claimed_at` timestamp NULL DEFAULT NULL,
              PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 3. admins table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `admins` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `username` varchar(255) NOT NULL,
              `email` varchar(255) DEFAULT NULL,
              `password_hash` varchar(255) NOT NULL,
              `display_name` varchar(255) DEFAULT 'Admin',
              `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
              PRIMARY KEY (`id`),
              UNIQUE KEY `username` (`username`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 4. admin_reward_logs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `admin_reward_logs` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `admin_id` int(11) NOT NULL,
              `player_id` int(11) NOT NULL,
              `reward_type` enum('stars','trophies') NOT NULL,
              `action` enum('add','deduct') NOT NULL,
              `amount` int(11) NOT NULL,
              `previous_balance` int(11) NOT NULL,
              `new_balance` int(11) NOT NULL,
              `reason` text DEFAULT NULL,
              `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
              PRIMARY KEY (`id`),
              FOREIGN KEY (`player_id`) REFERENCES `players`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 5. reward_announcements table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `reward_announcements` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `title` varchar(255) NOT NULL,
              `task_description` text NOT NULL,
              `reward_type` enum('stars','trophies') NOT NULL,
              `reward_amount` int(11) NOT NULL,
              `difficulty_target` varchar(50) DEFAULT 'Any',
              `theme_target` varchar(50) DEFAULT 'Any',
              `start_date` datetime NOT NULL,
              `end_date` datetime NOT NULL,
              `notification_message` text DEFAULT NULL,
              `status` enum('active','inactive') DEFAULT 'active',
              `created_by_admin` int(11) DEFAULT NULL,
              `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
              `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
              PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 6. reward_announcement_claims table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `reward_announcement_claims` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `announcement_id` int(11) NOT NULL,
              `player_id` int(11) NOT NULL,
              `is_completed` tinyint(1) NOT NULL DEFAULT 0,
              `is_claimed` tinyint(1) NOT NULL DEFAULT 0,
              `claimed_at` timestamp NULL DEFAULT NULL,
              `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
              `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
              PRIMARY KEY (`id`),
              UNIQUE KEY `unique_claim` (`announcement_id`, `player_id`),
              FOREIGN KEY (`announcement_id`) REFERENCES `reward_announcements`(`id`) ON DELETE CASCADE,
              FOREIGN KEY (`player_id`) REFERENCES `players`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 7. multiplayer_matches table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `multiplayer_matches` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `room_id` varchar(100) NOT NULL,
              `player_1_id` int(11) NOT NULL,
              `player_2_id` int(11) NOT NULL,
              `player_1_score` int(11) DEFAULT 0,
              `player_2_score` int(11) DEFAULT 0,
              `winner_id` int(11) DEFAULT NULL,
              `status` enum('waiting','active','completed','disconnected') DEFAULT 'waiting',
              `started_at` timestamp NULL DEFAULT NULL,
              `ended_at` timestamp NULL DEFAULT NULL,
              `duration_seconds` int(11) DEFAULT 0,
              `disconnected_player_id` int(11) DEFAULT NULL,
              `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
              `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
              PRIMARY KEY (`id`),
              KEY `idx_room` (`room_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 8. Ensure players columns exist
            _safe_alter(cursor, "ALTER TABLE players ADD COLUMN username varchar(255) DEFAULT NULL")
            _safe_alter(cursor, "ALTER TABLE players ADD COLUMN password_hash varchar(255) DEFAULT NULL")
            _safe_alter(cursor, "ALTER TABLE players ADD COLUMN profile_picture varchar(255) DEFAULT NULL")
            _safe_alter(cursor, "ALTER TABLE players ADD COLUMN fcm_token varchar(500) DEFAULT NULL")
            _safe_alter(cursor, "ALTER TABLE players ADD COLUMN stars INT(11) NOT NULL DEFAULT 0")
            _safe_alter(cursor, "ALTER TABLE players ADD COLUMN last_login TIMESTAMP NULL DEFAULT NULL")

            # 9. Auto-seed admin account from env vars (only if not exists)
            admin_username = os.getenv("ADMIN_USERNAME", "yvezjayveegesmundo")
            admin_password = os.getenv("ADMIN_PASSWORD", "thethethe")
            admin_email    = os.getenv("ADMIN_EMAIL", admin_username)

            cursor.execute("SELECT id FROM admins WHERE username = %s", (admin_username,))
            if not cursor.fetchone():
                try:
                    import bcrypt
                    pw_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                except ImportError:
                    import hashlib
                    pw_hash = hashlib.sha256(admin_password.encode()).hexdigest()

                cursor.execute(
                    "INSERT INTO admins (username, email, password_hash, display_name) VALUES (%s, %s, %s, %s)",
                    (admin_username, admin_email, pw_hash, "Admin")
                )
                print(f"[DB] Admin account '{admin_username}' created.")
            else:
                print(f"[DB] Admin account '{admin_username}' already exists.")

            db.commit()
        db.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Warning: Failed to initialize database schemas: {e}")
