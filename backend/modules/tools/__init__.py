from fastapi import APIRouter

from core.auth.dependencies import get_current_user
from core.database import get_db
from modules.tools.base import BaseTool

router = APIRouter(prefix="/api/tools", tags=["tools"])

_tool_registry: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool) -> None:
    _tool_registry[tool.slug] = tool
