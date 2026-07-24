"""AI Plugin System — plugins that AI can invoke to answer user questions.

Each plugin has:
  - name: unique name
  - description: what it does (for AI to decide)
  - patterns: regex patterns to auto-trigger
  - execute(text): async function returning answer string

AI Router checks plugins before calling providers.
If a plugin matches, no API call is made.
"""
import importlib
import logging
import os
import pkgutil
import re

logger = logging.getLogger(__name__)

_plugins: list[dict] = []


def register(name: str, description: str, patterns: list[str] = None):
    """Decorator to register an AI plugin."""
    def decorator(func):
        _plugins.append({
            "name": name,
            "description": description,
            "patterns": patterns or [],
            "func": func,
        })
        return func
    return decorator


def get_plugin_list() -> list[dict]:
    """Return all registered plugins for AI context."""
    return [{"name": p["name"], "description": p["description"]} for p in _plugins]


async def match_and_execute(text: str) -> str | None:
    """Check all plugins. If one matches, execute and return result."""
    for plugin in _plugins:
        for pattern in plugin["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                try:
                    result = await plugin["func"](text)
                    if result:
                        return result
                except Exception as e:
                    logger.warning(f"Plugin {plugin['name']} error: {e}")
    return None


def load_plugins():
    """Auto-discover and load all plugin modules."""
    plugin_dir = os.path.join(os.path.dirname(__file__))
    for importer, modname, is_pkg in pkgutil.iter_modules([plugin_dir]):
        if modname.startswith("_") or modname == "ai_plugin_system":
            continue
        try:
            importlib.import_module(f"handlers.plugins.{modname}")
            logger.info(f"Plugin loaded: {modname}")
        except Exception as e:
            logger.error(f"Plugin {modname} failed: {e}")


# ─── Built-in plugins ───

@register("calculator", "محاسبه عبارات ریاضی", [r"[\d\+\-\*\/\(\)\^\%]+", r"cos|sin|tan|sqrt|log|abs"])
async def plugin_calculator(text: str) -> str | None:
    try:
        import math
        allowed = text.replace("^", "**")
        # Only allow safe math
        safe = re.sub(r'[^\d\s\+\-\*\/\(\)\%\.\,\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ ]', '', allowed)
        if not safe:
            return None
        # Use math.eval via safer method
        result = eval(safe, {"__builtins__": {}}, {"abs": abs, "round": round, "int": int, "float": float})
        return f"🧮 {text} = {result}"
    except:
        return None


@register("translate", "ترجمه متن به فارسی یا انگلیسی", [r"(translate|ترجمه|معنی|meaning of|to persian|to english|به فارسی|به انگلیسی)"])
async def plugin_translate(text: str) -> str | None:
    # Simplified: just return None and let AI handle it
    return None


@register("weather", "گرفتن وضعیت آب و هوای یک شهر", [r"(weather|آب و هوا|هوا|temperature|دما|باران|برف|آفتاب)"])
async def plugin_weather(text: str) -> str | None:
    # Placeholder — requires weather API key
    return None
