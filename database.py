import asyncio
import aiosqlite
import os
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

CANDIDATE_PATHS = [
    '/data/bot_data.db',
    '/tmp/bot_data.db',
    DATABASE_PATH,
    '/app/bot_data.db',
    'bot_data.db',
]


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.resolved_path = None
        self.db: aiosqlite.Connection | None = None

    async def connect(self):
        for attempt in range(10):
            for path in CANDIDATE_PATHS:
                try:
                    db_dir = os.path.dirname(path)
                    if db_dir:
                        os.makedirs(db_dir, exist_ok=True)
                    test_file = os.path.join(db_dir or '.', '.write_test')
                    with open(test_file, 'w') as f:
                        f.write('ok')
                    os.remove(test_file)
                    self.resolved_path = path
                    break
                except:
                    continue
            if self.resolved_path:
                break
            if attempt < 9:
                await asyncio.sleep(2)
        if not self.resolved_path:
            self.resolved_path = '/tmp/bot_data.db'
        self.db = await aiosqlite.connect(self.resolved_path)
        self.db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self.db:
            await self.db.close()

    async def _create_tables(self):
        await self.db.executescript("""
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

            CREATE INDEX IF NOT EXISTS idx_chat_history_chat_ts ON chat_history(chat_id, timestamp);

            CREATE TABLE IF NOT EXISTS ai_persona (
                chat_id INTEGER PRIMARY KEY,
                persona_name TEXT DEFAULT 'کُتلت',
                system_prompt TEXT DEFAULT 'تو یک ربات هوشمند به نام کُتلت هستی. محاوره‌ای و خودمونی حرف بزن.',
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
        """)
        await self.db.commit()

    async def set_welcome(self, chat_id: int, message: str | None = None, is_enabled: bool = True):
        await self.db.execute(
            "INSERT OR REPLACE INTO welcome_settings (chat_id, message, is_enabled) VALUES (?, ?, ?)",
            (chat_id, message, int(is_enabled))
        )
        await self.db.commit()

    async def get_welcome(self, chat_id: int) -> dict | None:
        async with self.db.execute("SELECT * FROM welcome_settings WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"message": row["message"], "is_enabled": bool(row["is_enabled"])}
            return None

    async def set_rules(self, chat_id: int, rules_text: str):
        await self.db.execute(
            "INSERT OR REPLACE INTO rules (chat_id, rules_text) VALUES (?, ?)",
            (chat_id, rules_text)
        )
        await self.db.commit()

    async def get_rules(self, chat_id: int) -> str | None:
        async with self.db.execute("SELECT rules_text FROM rules WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return row["rules_text"] if row else None

    async def log_spam(self, chat_id: int, user_id: int, message_text: str):
        await self.db.execute(
            "INSERT INTO spam_log (chat_id, user_id, message_text) VALUES (?, ?, ?)",
            (chat_id, user_id, message_text)
        )
        await self.db.commit()

    async def get_spam_count(self, chat_id: int, user_id: int, window_seconds: int = 10) -> int:
        async with self.db.execute(
            "SELECT COUNT(*) as cnt FROM spam_log WHERE chat_id = ? AND user_id = ? AND timestamp > datetime('now', ?)",
            (chat_id, user_id, f"-{window_seconds} seconds")
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def clear_spam_log(self, chat_id: int, user_id: int):
        await self.db.execute(
            "DELETE FROM spam_log WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        await self.db.commit()

    async def ban_user(self, chat_id: int, user_id: int, reason: str = ""):
        await self.db.execute(
            "INSERT OR REPLACE INTO banned_users (chat_id, user_id, reason) VALUES (?, ?, ?)",
            (chat_id, user_id, reason)
        )
        await self.db.commit()

    async def unban_user(self, chat_id: int, user_id: int):
        await self.db.execute("DELETE FROM banned_users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        await self.db.commit()

    async def is_banned(self, chat_id: int, user_id: int) -> bool:
        async with self.db.execute("SELECT 1 FROM banned_users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)) as cursor:
            return await cursor.fetchone() is not None

    async def mute_user(self, chat_id: int, user_id: int, duration: int = 0, reason: str = ""):
        await self.db.execute(
            "INSERT OR REPLACE INTO muted_users (chat_id, user_id, reason, mute_duration) VALUES (?, ?, ?, ?)",
            (chat_id, user_id, reason, duration)
        )
        await self.db.commit()

    async def unmute_user(self, chat_id: int, user_id: int):
        await self.db.execute("DELETE FROM muted_users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        await self.db.commit()

    async def is_muted(self, chat_id: int, user_id: int) -> bool:
        async with self.db.execute("SELECT 1 FROM muted_users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)) as cursor:
            return await cursor.fetchone() is not None

    async def save_chat(self, chat_id: int, user_id: int, message: str, response: str):
        await self.db.execute(
            "INSERT INTO chat_history (chat_id, user_id, message, response) VALUES (?, ?, ?, ?)",
            (chat_id, user_id, message, response)
        )
        await self.db.commit()

    async def get_chat_history(self, chat_id: int, limit: int = 10) -> list[dict]:
        async with self.db.execute(
            "SELECT message, response FROM chat_history WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
            (chat_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in reversed(rows):
                result.append({"role": "user", "content": r["message"]})
                result.append({"role": "assistant", "content": r["response"]})
            return result[:limit]

    async def set_persona(self, chat_id: int, name: str, system_prompt: str):
        await self.db.execute(
            "INSERT OR REPLACE INTO ai_persona (chat_id, persona_name, system_prompt) VALUES (?, ?, ?)",
            (chat_id, name, system_prompt)
        )
        await self.db.commit()

    async def get_persona(self, chat_id: int) -> dict | None:
        async with self.db.execute("SELECT * FROM ai_persona WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"name": row["persona_name"], "prompt": row["system_prompt"], "enabled": bool(row["is_enabled"])}
            return None

    async def toggle_persona(self, chat_id: int, enabled: bool):
        await self.db.execute("UPDATE ai_persona SET is_enabled = ? WHERE chat_id = ?", (int(enabled), chat_id))
        await self.db.commit()

    async def add_custom_command(self, chat_id: int, command: str, response: str, user_id: int):
        await self.db.execute(
            "INSERT OR REPLACE INTO custom_commands (chat_id, command, response, created_by) VALUES (?, ?, ?, ?)",
            (chat_id, command, response, user_id)
        )
        await self.db.commit()

    async def get_custom_command(self, chat_id: int, command: str) -> str | None:
        async with self.db.execute("SELECT response FROM custom_commands WHERE chat_id = ? AND command = ?", (chat_id, command)) as cursor:
            row = await cursor.fetchone()
            return row["response"] if row else None

    async def delete_custom_command(self, chat_id: int, command: str) -> bool:
        async with self.db.execute("SELECT 1 FROM custom_commands WHERE chat_id = ? AND command = ?", (chat_id, command)) as cursor:
            if await cursor.fetchone():
                await self.db.execute("DELETE FROM custom_commands WHERE chat_id = ? AND command = ?", (chat_id, command))
                await self.db.commit()
                return True
        return False

    async def list_custom_commands(self, chat_id: int) -> list[dict]:
        async with self.db.execute("SELECT command, response FROM custom_commands WHERE chat_id = ?", (chat_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"command": r["command"], "response": r["response"]} for r in rows]

    async def add_auto_reply(self, chat_id: int, keyword: str, response: str, user_id: int, is_regex: bool = False):
        await self.db.execute(
            "INSERT INTO auto_replies (chat_id, keyword, response, is_regex, created_by) VALUES (?, ?, ?, ?, ?)",
            (chat_id, keyword, response, int(is_regex), user_id)
        )
        await self.db.commit()

    async def get_auto_replies(self, chat_id: int) -> list[dict]:
        async with self.db.execute("SELECT keyword, response, is_regex FROM auto_replies WHERE chat_id = ?", (chat_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"keyword": r["keyword"], "response": r["response"], "is_regex": bool(r["is_regex"])} for r in rows]

    async def delete_auto_reply(self, chat_id: int, keyword: str) -> bool:
        async with self.db.execute("SELECT 1 FROM auto_replies WHERE chat_id = ? AND keyword = ?", (chat_id, keyword)) as cursor:
            if await cursor.fetchone():
                await self.db.execute("DELETE FROM auto_replies WHERE chat_id = ? AND keyword = ?", (chat_id, keyword))
                await self.db.commit()
                return True
        return False

    async def add_group(self, chat_id: int, title: str, username: str = "", member_count: int = 0):
        await self.db.execute(
            "INSERT OR REPLACE INTO bot_groups (chat_id, title, username, member_count, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (chat_id, title, username, member_count)
        )
        await self.db.commit()

    async def remove_group(self, chat_id: int):
        await self.db.execute("UPDATE bot_groups SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        await self.db.commit()

    async def get_all_groups(self) -> list[dict]:
        async with self.db.execute("SELECT chat_id, title, username, member_count FROM bot_groups WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [{"chat_id": r["chat_id"], "title": r["title"], "username": r["username"], "members": r["member_count"]} for r in rows]

    async def get_group_count(self) -> int:
        async with self.db.execute("SELECT COUNT(*) as cnt FROM bot_groups WHERE is_active = 1") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def update_group_member_count(self, chat_id: int, count: int):
        await self.db.execute("UPDATE bot_groups SET member_count = ?, updated_at = datetime('now') WHERE chat_id = ?", (count, chat_id))
        await self.db.commit()

    async def add_or_update_user(self, chat_id: int, user_id: int, username: str = "", full_name: str = "", is_admin: bool = False):
        existing = await self.get_user(chat_id, user_id)
        if existing:
            await self.db.execute(
                "UPDATE group_users SET username = ?, full_name = ?, is_admin = ?, last_seen = datetime('now') WHERE chat_id = ? AND user_id = ?",
                (username, full_name, int(is_admin), chat_id, user_id)
            )
        else:
            await self.db.execute(
                "INSERT INTO group_users (chat_id, user_id, username, full_name, is_admin) VALUES (?, ?, ?, ?, ?)",
                (chat_id, user_id, username, full_name, int(is_admin))
            )
        await self.db.commit()

    async def get_user(self, chat_id: int, user_id: int) -> dict | None:
        async with self.db.execute("SELECT * FROM group_users WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "full_name": row["full_name"],
                    "is_admin": bool(row["is_admin"]),
                    "message_count": row["message_count"],
                    "last_seen": row["last_seen"],
                    "first_seen": row["first_seen"]
                }
            return None

    async def increment_message_count(self, chat_id: int, user_id: int):
        await self.db.execute(
            "UPDATE group_users SET message_count = message_count + 1, last_seen = datetime('now') WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        await self.db.commit()

    async def get_group_users(self, chat_id: int) -> list[dict]:
        async with self.db.execute("SELECT * FROM group_users WHERE chat_id = ? ORDER BY message_count DESC", (chat_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": r["user_id"], "username": r["username"], "full_name": r["full_name"], "messages": r["message_count"]} for r in rows]

    async def get_all_users(self) -> list[dict]:
        async with self.db.execute("SELECT DISTINCT user_id, username, full_name, COUNT(DISTINCT chat_id) as group_count FROM group_users GROUP BY user_id") as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": r["user_id"], "username": r["username"], "full_name": r["full_name"], "groups": r["group_count"]} for r in rows]

    async def set_group_settings(self, chat_id: int, **kwargs):
        current = await self.get_group_settings(chat_id)
        if not current:
            await self.db.execute("INSERT INTO group_settings (chat_id) VALUES (?)", (chat_id,))
        
        for key, value in kwargs.items():
            if key in ["force_sub_channel", "force_sub_enabled", "welcome_enabled", "spam_protection", "flood_protection", "ai_chat_enabled", "custom_title"]:
                await self.db.execute(f"UPDATE group_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id))
        await self.db.commit()

    async def get_group_settings(self, chat_id: int) -> dict | None:
        async with self.db.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "force_sub_channel": row["force_sub_channel"],
                    "force_sub_enabled": bool(row["force_sub_enabled"]),
                    "welcome_enabled": bool(row["welcome_enabled"]),
                    "spam_protection": bool(row["spam_protection"]),
                    "flood_protection": bool(row["flood_protection"]),
                    "ai_chat_enabled": bool(row["ai_chat_enabled"]),
                    "custom_title": row["custom_title"]
                }
            return None


db = Database()
