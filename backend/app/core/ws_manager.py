"""
Gestionnaire de connexions WebSocket (§34).
Les routers FastAPI restent synchrones (SQLAlchemy ORM classique) ; `broadcast_sync`
permet de programmer l'envoi asynchrone depuis ce contexte sync via la boucle
d'événements capturée au démarrage de l'app (voir main.py).
"""

import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, list[WebSocket]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        await websocket.accept()
        self.active.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        conns = self.active.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns and user_id in self.active:
            del self.active[user_id]

    async def send_to_user(self, user_id: int, event: dict) -> None:
        for ws in list(self.active.get(user_id, [])):
            await ws.send_json(event)

    async def broadcast(self, event: dict, exclude_user_id: int | None = None) -> None:
        for uid, conns in list(self.active.items()):
            if uid == exclude_user_id:
                continue
            for ws in list(conns):
                await ws.send_json(event)

    def broadcast_sync(self, event: dict, exclude_user_id: int | None = None) -> None:
        """À appeler depuis un endpoint/route sync après un commit DB."""
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(event, exclude_user_id), self.loop)

    def send_to_user_sync(self, user_id: int, event: dict) -> None:
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.send_to_user(user_id, event), self.loop)


manager = ConnectionManager()
