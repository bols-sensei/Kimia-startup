"""
Domaine Contenu : platforms, publications, publication_platforms.

`platforms` n'était pas explicitement nommée dans le dossier initial (seulement
évoquée comme "table intermédiaire" avec Instagram/Facebook/TikTok/LinkedIn) —
ajoutée ici pour porter proprement la relation N-N. À confirmer que ces 4
plateformes suffisent pour le MVP (table de données, extensible sans migration).
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PublicationStatus(str, enum.Enum):
    BROUILLON = "BROUILLON"
    A_VALIDER = "A_VALIDER"
    VALIDE = "VALIDE"
    A_MODIFIER = "A_MODIFIER"


class PublicationFormat(str, enum.Enum):
    IMAGE = "IMAGE"
    CAROUSEL = "CAROUSEL"
    REEL = "REEL"
    STORY = "STORY"
    VIDEO = "VIDEO"
    TEXT = "TEXT"
    LINK = "LINK"


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    publication_platforms: Mapped[list["PublicationPlatform"]] = relationship(
        back_populates="platform", cascade="all, delete-orphan"
    )


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[PublicationFormat | None] = mapped_column(nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[PublicationStatus] = mapped_column(
        default=PublicationStatus.BROUILLON, nullable=False
    )
    media: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # chemins des médias associés
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    publication_platforms: Mapped[list["PublicationPlatform"]] = relationship(
        back_populates="publication", cascade="all, delete-orphan"
    )

    @property
    def platform_ids(self) -> list[int]:
        return [pp.platform_id for pp in self.publication_platforms]


class PublicationPlatform(Base):
    __tablename__ = "publication_platforms"

    publication_id: Mapped[int] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), primary_key=True
    )
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="CASCADE"), primary_key=True
    )

    publication: Mapped["Publication"] = relationship(back_populates="publication_platforms")
    platform: Mapped["Platform"] = relationship(back_populates="publication_platforms")
class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )