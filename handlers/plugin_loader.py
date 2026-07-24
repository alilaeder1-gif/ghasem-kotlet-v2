"""Simple plugin loader for hot-swappable feature modules.

Plugins are Python files inside handlers/plugins/ directory.
Each plugin must have a `router` attribute (aiogram Router) and
a `__plugin_name__` string and `__plugin_version__` string.
"""
import importlib
import logging
import os
import pkgutil

logger = logging.getLogger(__name__)

_loaded_plugins: dict[str, dict] = {}


def discover_plugins(plugin_dir: str = None) -> list[dict]:
    """Discover all plugins in the plugins directory."""
    if plugin_dir is None:
        plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")

    if not os.path.isdir(plugin_dir):
        os.makedirs(plugin_dir, exist_ok=True)
        init_file = os.path.join(plugin_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# plugins package\n")
        return []

    plugins = []
    for importer, modname, is_pkg in pkgutil.iter_modules([plugin_dir]):
        if is_pkg or modname.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"handlers.plugins.{modname}")
            plugin_info = {
                "name": getattr(mod, "__plugin_name__", modname),
                "version": getattr(mod, "__plugin_version__", "0.1"),
                "description": getattr(mod, "__plugin_description__", ""),
                "router": getattr(mod, "router", None),
                "module": mod,
            }
            plugins.append(plugin_info)
            logger.info(f"Plugin loaded: {plugin_info['name']} v{plugin_info['version']}")
        except Exception as e:
            logger.error(f"Failed to load plugin {modname}: {e}")

    return plugins


def load_plugins() -> list:
    """Load all plugins and return their routers."""
    global _loaded_plugins
    plugins = discover_plugins()
    routers = []
    for p in plugins:
        if p["router"]:
            routers.append(p["router"])
            _loaded_plugins[p["name"]] = p
    logger.info(f"Loaded {len(routers)} plugin router(s)")
    return routers
