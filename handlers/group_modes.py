import logging
from database import db

logger = logging.getLogger(__name__)

GROUP_MODES = {
    "cafe": {
        "name": "☕ Cafe Mode",
        "label": "گپ دوستانه",
        "humor": 7,
        "energy": 6,
        "formality": 2,
        "help": 3,
        "jargon": "general",
    },
    "gaming": {
        "name": "🎮 Gaming Mode",
        "label": "حالت بازی",
        "humor": 8,
        "energy": 9,
        "formality": 1,
        "help": 2,
        "jargon": "gaming",
    },
    "technical": {
        "name": "💻 Technical Mode",
        "label": "حالت فنی",
        "humor": 3,
        "energy": 5,
        "formality": 5,
        "help": 9,
        "jargon": "technical",
    },
    "friend": {
        "name": "🤝 Friend Mode",
        "label": "حالت دوستانه",
        "humor": 6,
        "energy": 8,
        "formality": 3,
        "help": 5,
        "jargon": "general",
    },
    "serious": {
        "name": "🧠 Serious Mode",
        "label": "حالت جدی",
        "humor": 2,
        "energy": 4,
        "formality": 8,
        "help": 7,
        "jargon": "formal",
    },
}

VALID_MODES = set(GROUP_MODES.keys())


async def get_group_mode(chat_id: int) -> dict:
    async with db.db.execute(
        "SELECT mode FROM group_modes WHERE chat_id = ?", (chat_id,)
    ) as cursor:
        row = await cursor.fetchone()
    mode = row["mode"] if row else "friend"
    return dict(GROUP_MODES.get(mode, GROUP_MODES["friend"]))


async def set_group_mode(chat_id: int, mode: str) -> bool:
    if mode not in VALID_MODES:
        return False
    await db.db.execute(
        "INSERT INTO group_modes (chat_id, mode) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET mode = excluded.mode",
        (chat_id, mode),
    )
    await db.db.commit()
    return True


def adjust_sliders_for_mode(base: dict, mode_config: dict) -> dict:
    adjusted = dict(base)
    humor_map = {"humor_level": "humor"}
    energy_map = {"energy": "energy"}
    for slider, mode_key in humor_map.items():
        if mode_key in mode_config:
            adjusted[slider] = int(mode_config[mode_key])
    for slider, mode_key in energy_map.items():
        if mode_key in mode_config:
            adjusted[slider] = int(mode_config[mode_key])
    return adjusted
