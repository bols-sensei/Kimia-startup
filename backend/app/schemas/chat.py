from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.chat import ChannelType


# --------------------------------------------------------------------------- #
# Canaux
# --------------------------------------------------------------------------- #

class ChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type: ChannelType
    project_id: int | None = None
    created_at: datetime
    # Champs calculés côté route
    last_message: "MessageRead | None" = None
    unread_count: int = 0
    message_count: int = 0


class ChannelCreate(BaseModel):
    name: str
    project_id: int | None = None


# --------------------------------------------------------------------------- #
# Messages
# --------------------------------------------------------------------------- #

class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    channel_id: int
    user_id: int | None
    content: str
    created_at: datetime
    edited_at: datetime | None = None
    # Champs calculés
    user_name: str | None = None
    user_initials: str | None = None


class MessageCreate(BaseModel):
    content: str


class MessageUpdate(BaseModel):
    content: str