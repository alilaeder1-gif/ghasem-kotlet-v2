import os
import sys
import time
import sqlite3

sys.path.insert(0, os.path.dirname(__file__))
from config import DATABASE_PATH

CANDIDATE_PATHS = [
    DATABASE_PATH,
    '/app/bot_data.db',
    '/tmp/bot_data.db',
    'bot_data.db',
]


def init_database():
    db_path = None
    for path in CANDIDATE_PATHS:
        for attempt in range(3):
            try:
                db_dir = os.path.dirname(path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)
                conn = sqlite3.connect(path)
                conn.close()
                db_path = path
                break
            except:
                time.sleep(1)
        if db_path:
            break

    if not db_path:
        raise Exception('No writable database path found')

    print(f'Database path: {db_path}')
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS welcome_settings (
            chat_id INTEGER PRIMARY KEY,
            message TEXT DEFAULT NULL,
            is_enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS rules (
            chat_id INTEGER PRIMARY KEY,
            rules_text TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS spam_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            message_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS banned_users (
            chat_id INTEGER,
            user_id INTEGER,
            reason TEXT DEFAULT '',
            banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS muted_users (
            chat_id INTEGER,
            user_id INTEGER,
            reason TEXT DEFAULT '',
            muted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            mute_duration INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ai_persona (
            chat_id INTEGER PRIMARY KEY,
            persona_name TEXT DEFAULT 'قاسم کتلت',
            system_prompt TEXT DEFAULT 'تو یک ربات هوشمند هستی. به فارسی پاسخ بده.',
            is_enabled INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS custom_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            command TEXT,
            response TEXT,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chat_id, command)
        );
        CREATE TABLE IF NOT EXISTS auto_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            keyword TEXT,
            response TEXT,
            is_regex INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS bot_groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT DEFAULT '',
            username TEXT DEFAULT '',
            member_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS group_users (
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            message_count INTEGER DEFAULT 0,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS group_settings (
            chat_id INTEGER PRIMARY KEY,
            force_sub_channel TEXT DEFAULT '',
            force_sub_enabled INTEGER DEFAULT 0,
            welcome_enabled INTEGER DEFAULT 1,
            spam_protection INTEGER DEFAULT 1,
            flood_protection INTEGER DEFAULT 1,
            ai_chat_enabled INTEGER DEFAULT 1,
            custom_title TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS panel_config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()
    print('Database initialized successfully!')
    return db_path


if __name__ == '__main__':
    for i in range(5):
        try:
            db_path = init_database()
            print(f'Database ready at: {db_path}')
            sys.exit(0)
        except Exception as e:
            print(f'Attempt {i+1}/5 failed: {e}')
            time.sleep(3)
    print('Failed to initialize database! Bot will create tables on startup.')
    sys.exit(0)
