import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.exceptions import register_exception_handlers
from core.websocket import manager
from core.auth.jwt import decode_access_token
from modules import discover_modules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("coffee_time_saver")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await manager.startup()
    modules = discover_modules()
    for mod in modules:
        try:
            await mod.initialize()
        except Exception as e:
            logger.error("Module %s failed to initialize: %s", mod.slug, e)
    app.state.modules = modules
    logger.info("Coffee Time Saver backend started. Loaded %d modules.", len(modules))
    yield
    # Shutdown
    await manager.shutdown()


app = FastAPI(
    title="Coffee Time Saver API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Register module routers after discover (done during lifespan, but need eager import)
# Import routers here so they're available immediately
from modules.auth.router import router as auth_router
from modules.dashboard.router import router as dashboard_router
from modules.tasks.router import router as tasks_router
from modules.projects.router import router as projects_router
from modules.briefing.router import router as briefing_router
from modules.file_processing.router import router as files_router
from modules.settings.router import router as settings_router
from modules.tools.router import router as tools_router
from modules.tools.risk_analyzer.router import router as risk_router
from modules.email_bot.oauth_router import router as email_oauth_router

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(tasks_router)
app.include_router(projects_router)
app.include_router(briefing_router)
app.include_router(files_router)
app.include_router(settings_router)
app.include_router(tools_router)
app.include_router(risk_router)
app.include_router(email_oauth_router)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=1008)
        return

    user_id = uuid.UUID(payload["sub"])
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive; clients can send pings
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@app.get("/health")
async def health():
    return {"status": "ok"}
