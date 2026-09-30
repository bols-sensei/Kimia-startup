import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from app.routers import cron
from .config import settings
from .core.ws_manager import manager
from app.routers import (
    activities,
    auth,
    chat,
    clients,
    documents,
    finance,
    notifications,
    portfolio,      # ← AJOUT
    projects,
    public,
    positions,    # ← AJOUT
    skills,    
    publications,
    requests as requests_router,
    security,
    services,       # ← AJOUT
    users,
    ws,
)
FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Capture la boucle asyncio en cours pour permettre à manager.broadcast_sync(...)
    # d'être appelé depuis les routers synchrones (voir app/core/ws_manager.py).
    manager.set_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="Kimia API", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(requests_router.router, prefix="/api/requests", tags=["requests"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(publications.router, prefix="/api/publications", tags=["publications"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(finance.router, prefix="/api/finance", tags=["finance"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(security.router, prefix="/api/security", tags=["security"])
app.include_router(ws.router, tags=["websocket"])  # /ws
app.include_router(services.router, prefix="/api/services", tags=["services"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(cron.router, prefix="/api/cron", tags=["cron"])

@app.get("/")
def root():
    return RedirectResponse(url="/public/")


app.mount(
    "/public",
    StaticFiles(directory=FRONTEND / "public", html=True),
    name="public",
)
app.mount(
    "/app",
    StaticFiles(directory=FRONTEND / "app", html=True),
    name="app",
)
app.mount(
    "/assets",
    StaticFiles(directory=FRONTEND / "assets"),
    name="assets",
)
app.mount(
    "/storage",
    StaticFiles(directory="storage"),
    name="storage",
)