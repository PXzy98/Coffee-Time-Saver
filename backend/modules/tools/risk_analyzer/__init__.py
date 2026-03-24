from modules.tools.base import BaseTool
from modules.tools.risk_analyzer.router import router as _router


class RiskAnalyzerTool(BaseTool):
    slug = "risk-analyzer"
    router = _router

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}

    async def execute(self, payload: dict, user_id: str) -> dict:
        return {"message": "Use POST /api/tools/risk-analyzer/run"}


module_instance = RiskAnalyzerTool()
