import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.ws_manager import manager
from app.routers import (
    access, activities, auth, cash, chat, clients, cron, dev, documents,
    finance, notifications, portfolio, positions, projects, public,
    publications, requests as requests_router, security, services, skills,
    users, ws,
)
from app.seed_first_admin import run as run_seed

FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.set_loop(asyncio.get_running_loop())
    run_seed()
    yield


app = FastAPI(title="Kimia API", version="0.1.0", lifespan=lifespan)

# ===== ROUTERS =====
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
app.include_router(ws.router, tags=["websocket"])
app.include_router(services.router, prefix="/api/services", tags=["services"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(cron.router, prefix="/api/cron", tags=["cron"])
app.include_router(cash.router, prefix="/api/cash", tags=["cash"])
app.include_router(access.router, prefix="/api/access", tags=["access"])
app.include_router(dev.router, prefix="/api/dev", tags=["dev"])


@app.get("/")
def root():
    return RedirectResponse(url="/public/")


# ===== STATIQUES =====
app.mount("/public", StaticFiles(directory=FRONTEND / "public", html=True), name="public")
app.mount("/app", StaticFiles(directory=FRONTEND / "app", html=True), name="app")
app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

Path("storage/portfolio").mkdir(parents=True, exist_ok=True)
app.mount("/storage/portfolio", StaticFiles(directory="storage/portfolio"), name="storage_portfolio")