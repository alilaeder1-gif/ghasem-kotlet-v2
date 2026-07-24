import asyncio
import aiosqlite
import os
import re
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
        try:
            await self.db.execute("PRAGMA journal_mode=WAL")
        except:
            pass
        try:
            await self.db.execute("PRAGMA busy_timeout=5000")
        except:
            pass
        await self._create_tables()

    async def close(self):
        if self.db:
            await self.db.close()

    async def _create_tables(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS qa_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                question TEXT,
                answer TEXT,
                keywords TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_qa_memory_chat ON qa_memory(chat_id);
            CREATE INDEX IF NOT EXISTS idx_qa_memory_keywords ON qa_memory(keywords);

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
                invite_link TEXT DEFAULT '',
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

            CREATE TABLE IF NOT EXISTS personality_sliders (
                chat_id INTEGER PRIMARY KEY,
                friendliness INTEGER DEFAULT 9,
                humor_level INTEGER DEFAULT 9,
                sarcasm_level INTEGER DEFAULT 6,
                confidence INTEGER DEFAULT 9,
                empathy INTEGER DEFAULT 8,
                tehran_accent INTEGER DEFAULT 9,
                street_language INTEGER DEFAULT 8,
                energy INTEGER DEFAULT 9,
                patience INTEGER DEFAULT 6
            );

            CREATE TABLE IF NOT EXISTS user_memory (
                user_id INTEGER,
                chat_id INTEGER,
                memory TEXT DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            );

            CREATE TABLE IF NOT EXISTS user_relationships (
                user_id INTEGER,
                chat_id INTEGER,
                preferred_name TEXT DEFAULT '',
                speaking_style TEXT DEFAULT 'default',
                humor_preference INTEGER DEFAULT 5,
                technical_level INTEGER DEFAULT 5,
                interaction_mood TEXT DEFAULT 'neutral',
                last_topic TEXT DEFAULT '',
                total_interactions INTEGER DEFAULT 0,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, chat_id)
            );

            CREATE TABLE IF NOT EXISTS group_modes (
                chat_id INTEGER PRIMARY KEY,
                mode TEXT DEFAULT 'friend',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS character_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phrase TEXT,
                category TEXT,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                last_used DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(phrase, category)
            );

            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                message_id INTEGER DEFAULT 0,
                feedback_type TEXT,
                response_text TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ab_test (
                chat_id INTEGER PRIMARY KEY,
                variant TEXT NOT NULL DEFAULT 'A',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ab_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                variant TEXT,
                feedback_type TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                user_message TEXT,
                bot_response TEXT,
                response_length INTEGER DEFAULT 0,
                emotion_detected TEXT DEFAULT '',
                humor_used INTEGER DEFAULT 0,
                hallucination_risky INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0,
                passed_quality_gate INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings_access (
                chat_id INTEGER,
                user_id INTEGER,
                granted_by INTEGER DEFAULT 0,
                granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await self.db.commit()
        await self._migrate_old()
        await self._init_api_tables()

    async def _init_api_tables(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                enabled INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                api_key TEXT NOT NULL,
                status TEXT DEFAULT 'healthy',
                health REAL DEFAULT 100.0,
                cooldown_until DATETIME,
                requests_today INTEGER DEFAULT 0,
                total_calls INTEGER DEFAULT 0,
                last_used DATETIME,
                last_error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES providers(id)
            );
            INSERT OR IGNORE INTO providers (name) VALUES ('gemini');
            INSERT OR IGNORE INTO providers (name) VALUES ('groq');
            INSERT OR IGNORE INTO providers (name) VALUES ('openrouter');
        """)
        await self.db.commit()

    async def get_provider_id(self, name: str) -> int | None:
        async with self.db.execute("SELECT id FROM providers WHERE name = ?", (name,)) as cursor:
            row = await cursor.fetchone()
            return row["id"] if row else None

    async def add_api_key(self, provider: str, api_key: str):
        pid = await self.get_provider_id(provider)
        if pid is None: return
        await self.db.execute(
            "INSERT INTO api_keys (provider_id, api_key) VALUES (?, ?)",
            (pid, api_key)
        )
        await self.db.commit()

    async def remove_api_key(self, key_id: int):
        await self.db.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        await self.db.commit()

    async def update_key_status(self, key_id: int, **kwargs):
        cols = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [key_id]
        await self.db.execute(f"UPDATE api_keys SET {cols} WHERE id = ?", vals)
        await self.db.commit()

    async def get_healthy_keys(self, provider: str) -> list[dict]:
        pid = await self.get_provider_id(provider)
        if pid is None: return []
        async with self.db.execute(
            "SELECT id, api_key, status, health, cooldown_until, requests_today, total_calls, last_error "
            "FROM api_keys WHERE provider_id = ? AND status = 'healthy' "
            "AND (cooldown_until IS NULL OR cooldown_until < datetime('now')) "
            "ORDER BY health DESC, last_used ASC",
            (pid,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_keys(self, provider: str = None) -> list[dict]:
        if provider:
            pid = await self.get_provider_id(provider)
            if pid is None: return []
            async with self.db.execute(
                "SELECT id, api_key, status, health, cooldown_until, requests_today, total_calls, last_error, last_used "
                "FROM api_keys WHERE provider_id = ? ORDER BY health DESC", (pid,)
            ) as cursor:
                return [dict(r) for r in await cursor.fetchall()]
        async with self.db.execute(
            "SELECT ak.id, p.name as provider, ak.api_key, ak.status, ak.health, "
            "ak.cooldown_until, ak.requests_today, ak.total_calls, ak.last_error "
            "FROM api_keys ak JOIN providers p ON ak.provider_id = p.id ORDER BY p.name, ak.health DESC"
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

    async def seed_api_keys_from_env(self):
        from config import GEMINI_KEYS, GROQ_KEYS, OPENROUTER_KEYS
        for provider, keys in [("gemini", GEMINI_KEYS), ("groq", GROQ_KEYS), ("openrouter", OPENROUTER_KEYS)]:
            pid = await self.get_provider_id(provider)
            if pid is None: continue
            async with self.db.execute("SELECT COUNT(*) as cnt FROM api_keys WHERE provider_id = ?", (pid,)) as cursor:
                row = await cursor.fetchone()
                if row["cnt"] > 0: continue
            for key in keys:
                if key:
                    await self.db.execute(
                        "INSERT INTO api_keys (provider_id, api_key) VALUES (?, ?)", (pid, key)
                    )
        await self.db.commit()

    async def get_key_count(self) -> int:
        async with self.db.execute("SELECT COUNT(*) as cnt FROM api_keys") as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def _migrate_old(self):
        try:
            await self.db.execute("ALTER TABLE bot_groups ADD COLUMN invite_link TEXT DEFAULT ''")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN link_delete_enabled INTEGER DEFAULT 0")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN link_delete_delay INTEGER DEFAULT 0")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN ai_behavior TEXT DEFAULT 'default'")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN ai_tone TEXT DEFAULT 'tehrani'")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN ai_personality INTEGER DEFAULT 3")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN spam_config TEXT DEFAULT '{}'")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN flood_config TEXT DEFAULT '{}'")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN link_config TEXT DEFAULT '{}'")
            await self.db.commit()
        except:
            pass
        try:
            await self.db.execute("ALTER TABLE group_settings ADD COLUMN force_sub_config TEXT DEFAULT '[]'")
            await self.db.commit()
        except:
            pass

        # Personality sliders migration (new columns for v2.2.0)
        for col in ["tehran_accent", "street_language", "energy", "patience"]:
            try:
                await self.db.execute(f"ALTER TABLE personality_sliders ADD COLUMN {col} INTEGER DEFAULT 0")
                await self.db.commit()
            except:
                pass

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

    async def get_chat_history(self, chat_id: int, limit: int = 5) -> list[dict]:
        async with self.db.execute(
            "SELECT message, response FROM chat_history WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
            (chat_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for r in reversed(rows):
                result.append({"role": "user", "content": r["message"]})
                result.append({"role": "assistant", "content": r["response"]})
            return result

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

    async def add_group(self, chat_id: int, title: str, username: str = "", invite_link: str = "", member_count: int = 0):
        await self.db.execute(
            "INSERT OR REPLACE INTO bot_groups (chat_id, title, username, invite_link, member_count, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (chat_id, title, username, invite_link, member_count)
        )
        await self.db.commit()

    async def remove_group(self, chat_id: int):
        await self.db.execute("UPDATE bot_groups SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        await self.db.commit()

    async def get_all_groups(self) -> list[dict]:
        async with self.db.execute("SELECT chat_id, title, username, invite_link, member_count FROM bot_groups WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [{"chat_id": r["chat_id"], "title": r["title"], "username": r["username"], "invite_link": r["invite_link"], "members": r["member_count"]} for r in rows]

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
        async with self.db.execute("SELECT user_id, username, full_name, COUNT(DISTINCT chat_id) as group_count, MIN(first_seen) as first_seen FROM group_users GROUP BY user_id ORDER BY first_seen DESC") as cursor:
            rows = await cursor.fetchall()
            return [{"user_id": r["user_id"], "username": r["username"], "full_name": r["full_name"], "groups": r["group_count"], "first_seen": r["first_seen"]} for r in rows]

    async def set_group_settings(self, chat_id: int, **kwargs):
        import json
        current = await self.get_group_settings(chat_id)
        if not current:
            await self.db.execute("INSERT INTO group_settings (chat_id) VALUES (?)", (chat_id,))
        
        for key, value in kwargs.items():
            if key in ["force_sub_channel", "force_sub_enabled", "welcome_enabled", "spam_protection", "flood_protection", "ai_chat_enabled", "custom_title", "link_delete_enabled", "link_delete_delay", "ai_behavior", "ai_tone", "ai_personality"]:
                await self.db.execute(f"UPDATE group_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id))
            elif key in ["spam_config", "flood_config", "link_config", "force_sub_config"]:
                await self.db.execute(f"UPDATE group_settings SET {key} = ? WHERE chat_id = ?", (json.dumps(value), chat_id))
        await self.db.commit()

    async def get_group_settings(self, chat_id: int) -> dict | None:
        async with self.db.execute("SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await self.db.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,))
                await self.db.commit()
                return {
                    "link_delete_enabled": False,
                    "link_delete_delay": 0,
                    "spam_config": {},
                    "flood_config": {},
                    "link_config": {},
                    "force_sub_config": [],
                    "ai_behavior": "default",
                    "ai_tone": "tehrani",
                    "ai_personality": 3,
                    "force_sub_channel": "",
                    "force_sub_enabled": False,
                    "welcome_enabled": True,
                    "spam_protection": True,
                    "flood_protection": True,
                    "ai_chat_enabled": True,
                    "custom_title": ""
                }
            import json
            return {
                "link_delete_enabled": bool(row["link_delete_enabled"]) if "link_delete_enabled" in row.keys() else False,
                "link_delete_delay": row["link_delete_delay"] if "link_delete_delay" in row.keys() else 0,
                "spam_config": json.loads(row["spam_config"]) if "spam_config" in row.keys() and row["spam_config"] else {},
                "flood_config": json.loads(row["flood_config"]) if "flood_config" in row.keys() and row["flood_config"] else {},
                "link_config": json.loads(row["link_config"]) if "link_config" in row.keys() and row["link_config"] else {},
                "force_sub_config": json.loads(row["force_sub_config"]) if "force_sub_config" in row.keys() and row["force_sub_config"] else [],
                "ai_behavior": row["ai_behavior"] if "ai_behavior" in row.keys() else "default",
                "ai_tone": row["ai_tone"] if "ai_tone" in row.keys() else "tehrani",
                "ai_personality": row["ai_personality"] if "ai_personality" in row.keys() else 3,
                "force_sub_channel": row["force_sub_channel"],
                "force_sub_enabled": bool(row["force_sub_enabled"]),
                "welcome_enabled": bool(row["welcome_enabled"]),
                "spam_protection": bool(row["spam_protection"]),
                "flood_protection": bool(row["flood_protection"]),
                "ai_chat_enabled": bool(row["ai_chat_enabled"]),
                "custom_title": row["custom_title"]
            }

    async def get_user_memory(self, user_id: int, chat_id: int) -> str:
        async with self.db.execute("SELECT memory FROM user_memory WHERE user_id = ? AND chat_id = ?", (user_id, chat_id)) as cursor:
            row = await cursor.fetchone()
            return row["memory"] if row else ""

    async def save_user_memory(self, user_id: int, chat_id: int, memory: str):
        await self.db.execute(
            "INSERT OR REPLACE INTO user_memory (user_id, chat_id, memory, updated_at) VALUES (?, ?, ?, datetime('now'))",
            (user_id, chat_id, memory)
        )
        await self.db.commit()


    async def grant_settings_access(self, chat_id: int, user_id: int, granted_by: int = 0):
        await self.db.execute(
            "INSERT OR IGNORE INTO settings_access (chat_id, user_id, granted_by) VALUES (?, ?, ?)",
            (chat_id, user_id, granted_by)
        )
        await self.db.commit()

    async def revoke_settings_access(self, chat_id: int, user_id: int):
        await self.db.execute("DELETE FROM settings_access WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        await self.db.commit()

    async def has_settings_access(self, chat_id: int, user_id: int) -> bool:
        async with self.db.execute("SELECT 1 FROM settings_access WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)) as cursor:
            return await cursor.fetchone() is not None

    async def list_settings_access(self, chat_id: int) -> list[int]:
        async with self.db.execute("SELECT user_id FROM settings_access WHERE chat_id = ?", (chat_id,)) as cursor:
            rows = await cursor.fetchall()
            return [r["user_id"] for r in rows]


    async def save_qa_pair(self, chat_id: int, user_id: int, question: str, answer: str):
        keywords = " ".join(re.findall(r'[\wآ-ی]+', question.lower()))[:200]
        await self.db.execute(
            "INSERT INTO qa_memory (chat_id, user_id, question, answer, keywords) VALUES (?, ?, ?, ?, ?)",
            (chat_id, user_id, question[:300], answer[:500], keywords)
        )
        await self.db.commit()

    async def search_similar_qa(self, chat_id: int, query: str, limit: int = 3) -> list[dict]:
        words = re.findall(r'[\wآ-ی]+', query.lower())
        if not words:
            return []
        conditions = " OR ".join(["keywords LIKE ?"] * min(len(words), 5))
        params = [f"%{w}%" for w in words[:5]]
        try:
            async with self.db.execute(
                f"SELECT question, answer FROM qa_memory WHERE chat_id = ? AND ({conditions}) ORDER BY created_at DESC LIMIT ?",
                (chat_id, *params, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [{"question": r["question"], "answer": r["answer"]} for r in rows]
        except:
            return []

    async def count_qa_pairs(self, chat_id: int) -> int:
        async with self.db.execute("SELECT COUNT(*) as cnt FROM qa_memory WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0


    async def get_personality_sliders(self, chat_id: int) -> dict:
        async with self.db.execute(
            "SELECT * FROM personality_sliders WHERE chat_id = ?", (chat_id,)
        ) as cursor:
            row = await cursor.fetchone()
            default = {
                "friendliness": 9, "humor_level": 9, "sarcasm_level": 6,
                "confidence": 9, "empathy": 8, "tehran_accent": 9,
                "street_language": 8, "energy": 9, "patience": 6,
            }
            if row:
                result = {}
                for k in default:
                    result[k] = row[k] if k in row.keys() else default[k]
                return result
            return dict(default)

    async def set_personality_slider(self, chat_id: int, slider: str, value: int):
        await self.db.execute(
            f"INSERT INTO personality_sliders (chat_id, {slider}) VALUES (?, ?) "
            f"ON CONFLICT(chat_id) DO UPDATE SET {slider} = excluded.{slider}",
            (chat_id, value)
        )
        await self.db.commit()

    async def get_setting(self, key: str, default: str = "") -> str:
        async with self.db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row["value"] if row else default

    async def set_setting(self, key: str, value: str):
        await self.db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, value)
        )
        await self.db.commit()


db = Database()
