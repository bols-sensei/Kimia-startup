"""
Chat : canaux (#général + un par projet) et messages.

Règles :
- Le canal GLOBAL est unique et accessible à tous.
- Les canaux PROJECT sont créés automatiquement à la création d'un projet.
- Tout le monde peut lire et écrire dans tous les canaux accessibles.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user, require_permission
from app.core.ws_manager import manager
from app.database import get_db
from app.models import (
    Channel,
    ChannelMember,
    ChannelType,
    Message,
    Project,
    User,
)
from app.schemas.chat import (
    ChannelCreate,
    ChannelRead,
    MessageCreate,
    MessageRead,
    MessageUpdate,
)

router = APIRouter()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _get_global_channel(db: Session) -> Channel | None:
    """Récupère le canal #général (créé par le seed)."""
    return (
        db.query(Channel)
        .filter(Channel.type == ChannelType.GLOBAL)
        .order_by(Channel.id)
        .first()
    )


def _ensure_global_channel(db: Session) -> Channel:
    """Crée le canal #général s'il n'existe pas."""
    channel = _get_global_channel(db)
    if channel is None:
        channel = Channel(name="Général", type=ChannelType.GLOBAL)
        db.add(channel)
        db.commit()
        db.refresh(channel)
    return channel


def _can_access(channel: Channel, user: User, db: Session) -> bool:
    """Vérifie qu'un utilisateur peut accéder à un canal."""
    # Canal global : tout le monde
    if channel.type == ChannelType.GLOBAL:
        return True

    # Canal projet : CEO/DA toujours, CM si assigné au projet
    if user.role.name in ("CEO", "DA"):
        return True

    # CM : vérifier qu'il est assigné à une activité du projet
    if channel.project_id is None:
        return False

    from app.models import Activity, ActivityAssignment

    assigned = (
        db.query(ActivityAssignment)
        .join(Activity, Activity.id == ActivityAssignment.activity_id)
        .filter(
            Activity.project_id == channel.project_id,
            ActivityAssignment.user_id == user.id,
        )
        .first()
    )
    return assigned is not None


def _read_message(msg: Message) -> MessageRead:
    """Convertit un Message en MessageRead avec les infos utilisateur."""
    data = MessageRead.model_validate(msg)
    if msg.user:
        data.user_name = msg.user.name
        initials = "".join(p[0] for p in msg.user.name.split()[:2]).upper()
        data.user_initials = initials
    return data


def _read_channel(channel: Channel, user: User) -> ChannelRead:
    """Convertit un Channel en ChannelRead, avec le dernier message."""
    data = ChannelRead.model_validate(channel)
    if channel.messages:
        data.message_count = len(channel.messages)
        data.last_message = _read_message(channel.messages[-1])
    return data


# --------------------------------------------------------------------------- #
# Canaux
# --------------------------------------------------------------------------- #

@router.get("/channels", response_model=list[ChannelRead])
def list_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Liste des canaux accessibles à l'utilisateur."""
    _ensure_global_channel(db)

    channels = (
        db.query(Channel)
        .options(
            selectinload(Channel.messages).selectinload(Message.user),
        )
        .order_by(Channel.type, Channel.name)
        .all()
    )

    return [
        _read_channel(c, current_user)
        for c in channels
        if _can_access(c, current_user, db)
    ]


@router.post("/channels", response_model=ChannelRead, status_code=status.HTTP_201_CREATED)
def create_channel(
    payload: ChannelCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("team.manage")),
):
    """Créer un canal (CEO uniquement). Utile pour créer manuellement un canal projet."""
    if payload.project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un canal projet doit avoir un project_id",
        )

    if db.get(Project, payload.project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable",
        )

    # Vérifier qu'un canal projet n'existe pas déjà
    existing = (
        db.query(Channel)
        .filter(Channel.project_id == payload.project_id)
        .one_or_none()
    )
    if existing:
        return _read_channel(existing, _)

    channel = Channel(
        name=payload.name,
        type=ChannelType.PROJECT,
        project_id=payload.project_id,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return _read_channel(channel, _)


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #

@router.get("/channels/{channel_id}/messages", response_model=list[MessageRead])
def list_messages(
    channel_id: int,
    limit: int = 100,
    before_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Messages d'un canal, du plus récent au plus ancien (paginé)."""
    channel = db.get(Channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canal introuvable")

    if not _can_access(channel, current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    query = (
        db.query(Message)
        .options(selectinload(Message.user))
        .filter(Message.channel_id == channel_id)
    )
    if before_id is not None:
        query = query.filter(Message.id < before_id)

    messages = (
        query.order_by(Message.id.desc())
        .limit(min(limit, 200))
        .all()
    )

    # Inverser pour avoir l'ordre chronologique
    return [_read_message(m) for m in reversed(messages)]


@router.post(
    "/channels/{channel_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    channel_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envoyer un message dans un canal."""
    channel = db.get(Channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canal introuvable")

    if not _can_access(channel, current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message vide")

    message = Message(
        channel_id=channel_id,
        user_id=current_user.id,
        content=content,
    )
    db.add(message)

    # Marquer le canal comme lu pour l'auteur
    member = (
        db.query(ChannelMember)
        .filter_by(channel_id=channel_id, user_id=current_user.id)
        .one_or_none()
    )
    if member:
        member.last_read_at = datetime.now(timezone.utc)
    else:
        db.add(ChannelMember(channel_id=channel_id, user_id=current_user.id))

    db.commit()
    db.refresh(message)

    # Diffuser à tous les connectés
    manager.broadcast_sync({
        "type": "message.created",
        "data": {
            "channel_id": channel_id,
            "message_id": message.id,
            "user_id": current_user.id,
            "user_name": current_user.name,
            "content": content,
        },
    })

    return _read_message(message)


@router.patch("/messages/{message_id}", response_model=MessageRead)
def update_message(
    message_id: int,
    payload: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modifier un message (auteur uniquement)."""
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message introuvable")

    if message.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul l'auteur peut modifier")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message vide")

    message.content = content
    message.edited_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)

    manager.broadcast_sync({
        "type": "message.updated",
        "data": {"channel_id": message.channel_id, "message_id": message.id},
    })

    return _read_message(message)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supprimer un message (auteur ou CEO/DA)."""
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message introuvable")

    is_author = message.user_id == current_user.id
    is_admin = current_user.role.name in ("CEO", "DA")

    if not (is_author or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    channel_id = message.channel_id
    db.delete(message)
    db.commit()

    manager.broadcast_sync({
        "type": "message.deleted",
        "data": {"channel_id": channel_id, "message_id": message_id},
    })


@router.post("/channels/{channel_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_channel_read(
    channel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marquer un canal comme lu."""
    channel = db.get(Channel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canal introuvable")

    if not _can_access(channel, current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    member = (
        db.query(ChannelMember)
        .filter_by(channel_id=channel_id, user_id=current_user.id)
        .one_or_none()
    )
    if member:
        member.last_read_at = datetime.now(timezone.utc)
    else:
        db.add(ChannelMember(channel_id=channel_id, user_id=current_user.id))

    db.commit()