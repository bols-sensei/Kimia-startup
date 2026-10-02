from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.core.security import decode_access_token
from app.core.ws_manager import manager
from app.database import get_db
from app.models import User

router = APIRouter()


def _token_still_valid(app, user_id: int, token_version: int) -> bool:
    """Revérifie en base (session courte, libérée aussitôt) : compte actif et jeton non révoqué."""
    gen = app.dependency_overrides.get(get_db, get_db)()
    db = next(gen)
    try:
        user = db.get(User, user_id)
        return user is not None and user.is_active and user.token_version == token_version
    finally:
        gen.close()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = decode_access_token(token)
    valid = False
    if payload is not None:
        try:
            valid = await run_in_threadpool(
                _token_still_valid, websocket.app, int(payload["sub"]), int(payload.get("tv", 0))
            )
        except (KeyError, ValueError):
            valid = False
    if not valid:
        # On accepte puis on ferme avec un code applicatif (4401) : le client peut ainsi
        # distinguer "jeton invalide" d'une simple coupure réseau et ne pas boucler.
        await websocket.accept()
        await websocket.close(code=4401)
        return

    user_id = int(payload["sub"])
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Canal descendant serveur → client ; on lit pour détecter la déconnexion.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
