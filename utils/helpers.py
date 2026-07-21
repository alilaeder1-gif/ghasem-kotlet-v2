from datetime import datetime


def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} ثانیه"
    elif seconds < 3600:
        return f"{seconds // 60} دقیقه"
    elif seconds < 86400:
        return f"{seconds // 3600} ساعت"
    else:
        return f"{seconds // 86400} روز"


def parse_duration(duration_str: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    duration_str = duration_str.strip().lower()
    if not duration_str:
        return 0
    unit = duration_str[-1]
    if unit not in units:
        try:
            return int(duration_str)
        except ValueError:
            return 0
    try:
        value = int(duration_str[:-1])
        return value * units[unit]
    except ValueError:
        return 0


def time_ago(dt: datetime) -> str:
    now = datetime.now()
    diff = (now - dt).total_seconds()
    if diff < 60:
        return "همین الان"
    elif diff < 3600:
        return f"{int(diff // 60)} دقیقه پیش"
    elif diff < 86400:
        return f"{int(diff // 3600)} ساعت پیش"
    else:
        return f"{int(diff // 86400)} روز پیش"
