import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.db")

REDIS_URL = os.getenv("REDIS_URL", "") or os.getenv("REDIS_TLS_URL", "") or ""
REDIS_ENABLED = bool(REDIS_URL)

if DATABASE_PATH == '/app/data/bot_data.db':
    db_dir = '/app/data'
    try:
        os.makedirs(db_dir, exist_ok=True)
    except:
        DATABASE_PATH = '/app/bot_data.db'

WELCOME_MESSAGE = os.getenv(
    "WELCOME_MESSAGE",
    "سلام {name}! 👋\nبه گروه {group} خوش اومدی!\n\nقوانین گروه رو با /rules بخون."
)

SPAM_THRESHOLD = int(os.getenv("SPAM_THRESHOLD", "5"))
SPAM_WINDOW = int(os.getenv("SPAM_WINDOW", "10"))
FLOOD_THRESHOLD = int(os.getenv("FLOOD_THRESHOLD", "10"))
FLOOD_WINDOW = int(os.getenv("FLOOD_WINDOW", "10"))

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

HF_API_KEY = os.getenv("HF_API_KEY", "")

# Live settings (changed via /panel without deploy)
class LiveSettings:
    max_tokens = 256
    temperature = 1.0
    context_limit = 12000

settings = LiveSettings()
