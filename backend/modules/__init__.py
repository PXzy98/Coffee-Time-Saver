import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from modules.base import BaseModule

if TYPE_CHECKING:
    pass

logger = logging.getLogger("coffee_time_saver")

_MODULE_DIRS = [
    "auth", "dashboard", "tasks", "projects", "briefing",
    "file_processing", "ingestion", "email_bot", "llm_gateway", "settings",
]


def discover_modules() -> list[BaseModule]:
    """Auto-discover all backend modules that expose a module_instance."""
    discovered = []
    base_path = Path(__file__).parent

    for name in _MODULE_DIRS:
        module_path = base_path / name
        if not (module_path / "__init__.py").exists():
            continue
        try:
            mod = importlib.import_module(f"modules.{name}")
            if hasattr(mod, "module_instance"):
                discovered.append(mod.module_instance)
                logger.info("Loaded module: %s", name)
        except Exception as e:
            logger.error("Failed to load module %s: %s", name, e)

    # Load tool modules under modules/tools/
    tools_path = base_path / "tools"
    if tools_path.exists():
        for tool_dir in tools_path.iterdir():
            if tool_dir.is_dir() and (tool_dir / "__init__.py").exists():
                try:
                    mod = importlib.import_module(f"modules.tools.{tool_dir.name}")
                    if hasattr(mod, "module_instance"):
                        discovered.append(mod.module_instance)
                        logger.info("Loaded tool module: %s", tool_dir.name)
                except Exception as e:
                    logger.error("Failed to load tool module %s: %s", tool_dir.name, e)

    return discovered
