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
                            except Exception as e:
                                pass # Ignore errors if table already exists or index already exists
            
            # 2. Ensure rewards table exists (in case it's not in database.sql)
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
            
            # 3. Add missing columns to players table (ignore Error 1060 Duplicate column)
            try:
                cursor.execute("ALTER TABLE players ADD COLUMN username varchar(255) DEFAULT NULL")
            except pymysql.err.OperationalError as e:
                if e.args[0] != 1060: raise
                
            try:
                cursor.execute("ALTER TABLE players ADD COLUMN password_hash varchar(255) DEFAULT NULL")
            except pymysql.err.OperationalError as e:
                if e.args[0] != 1060: raise
                
            try:
                cursor.execute("ALTER TABLE players ADD COLUMN profile_picture varchar(255) DEFAULT NULL")
            except pymysql.err.OperationalError as e:
                if e.args[0] != 1060: raise

            try:
                cursor.execute("ALTER TABLE players ADD COLUMN fcm_token varchar(500) DEFAULT NULL")
            except pymysql.err.OperationalError as e:
                if e.args[0] != 1060: raise

            try:
                cursor.execute("ALTER TABLE players ADD COLUMN stars INT(11) NOT NULL DEFAULT 0")
            except pymysql.err.OperationalError as e:
                if e.args[0] != 1060: raise

            db.commit()
        db.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Warning: Failed to initialize database schemas: {e}")
