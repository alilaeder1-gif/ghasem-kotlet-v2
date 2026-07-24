"""
Four completely independent permission tiers:

  Tier               Source                          Access
  ──────────────────────────────────────────────────────────────
  Global Admin       ADMIN_IDS / bot_admins table     Bot management only
  Group Owner        telegram creator status          Full group control
  Group Admin        telegram administrator status    Member management
  Normal User        (everyone else)                  Basic bot features

These tiers NEVER mix. A Global Admin in a random group has NO
group management powers unless they are also a group admin there.
A Group Admin NEVER gets access to bot-level features.
"""

from config import ADMIN_IDS


# ════════════════════════════════════════════════════════════
# TIER 1 — Global Admin (bot management only)
# ════════════════════════════════════════════════════════════

def is_global_admin(user_id: int) -> bool:
    """Check if user is a global bot admin (ADMIN_IDS or bot_admins table)."""
    return user_id in ADMIN_IDS


# ════════════════════════════════════════════════════════════
# TIER 2 & 3 — Group Owner / Group Admin (telegram-level only)
# ════════════════════════════════════════════════════════════

async def _get_member_status(bot, chat_id: int, user_id: int) -> str | None:
    """Raw telegram membership status. Returns None on error."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status
    except Exception:
        return None


async def is_group_creator(bot, chat_id: int, user_id: int) -> bool:
    """Is the user the group creator (owner)?"""
    return (await _get_member_status(bot, chat_id, user_id)) == "creator"


async def is_group_admin(bot, chat_id: int, user_id: int) -> bool:
    """Is the user a group admin or creator?"""
    status = await _get_member_status(bot, chat_id, user_id)
    return status in ("creator", "administrator")
