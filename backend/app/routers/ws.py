from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.core.ws_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = decode_access_token(token)
    if payload is None:
        # On accepte puis on ferme avec un code applicatif (4401) : le client peut ainsi
        # distinguer "jeton invalide" d'une simple coupure réseau et ne pas boucler.
        await websocket.accept()
        await websocket.close(code=4401)
        return

    user_id = int(payload["sub"])
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Les messages entrants ne sont pas traités pour l'instant (canal
            # descendant serveur → client) ; on lit juste pour détecter la
            # déconnexion / garder la connexion vivante (ping côté client).
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
