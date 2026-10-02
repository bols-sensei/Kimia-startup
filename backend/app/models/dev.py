"""Équipe développement : membre (accès sur décision) vs dev interne (outils internes)."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DEV_LEVEL_INTERNAL = "INTERNAL"
DEV_LEVEL_MEMBER = "MEMBER"


class DevMembership(Base):
    __tablename__ = "dev_memberships"
    __table_args__ = (CheckConstraint("level in ('INTERNAL','MEMBER')", name="ck_dev_level"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    level: Mapped[str] = mapped_column(String(10), default=DEV_LEVEL_MEMBER, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    granted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="dev_membership", foreign_keys=[user_id])
