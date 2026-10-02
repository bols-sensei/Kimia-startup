"""
Domaine Authentification :
users, roles, permissions, role_permissions, skills, user_skills,
security_events, audit_logs, positions, position_skills, user_positions.

Principe : les rôles (CEO/DA/CM...) sont des DONNÉES (table roles), pas un enum
Python — cohérent avec "le code fournit le moteur, les données la configuration".
Seul le statut d'actionnariat (cofondateur / collaborateur) est un enum fermé.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# --------------------------------------------------------------------------- #
# Enums fermés
# --------------------------------------------------------------------------- #

class OwnershipStatus(str, enum.Enum):
    COFOUNDER = "COFOUNDER"
    COLLABORATOR = "COLLABORATOR"


# Statut professionnel (distinct de is_active, qui gouverne l'accès au compte).
EMPLOYMENT_STATUSES = ("ACTIVE", "ABSENT", "LEAVE", "SUSPENDED", "LEFT")


# --------------------------------------------------------------------------- #
# Rôles, permissions
# --------------------------------------------------------------------------- #

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="role")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    @property
    def permission_codes(self) -> set[str]:
        """Codes de permissions du rôle (ex: {'team.view', 'team.manage'})."""
        return {rp.permission.code for rp in self.role_permissions}


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")


# --------------------------------------------------------------------------- #
# Compétences
# --------------------------------------------------------------------------- #

class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    user_skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    position_skills: Mapped[list["PositionSkill"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


# --------------------------------------------------------------------------- #
# Postes (métiers) — configurables en base
# --------------------------------------------------------------------------- #

class Position(Base):
    """Poste métier : Développeur, Vidéaste, Graphiste, etc.
    Configurable en base, sans redéploiement."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    position_skills: Mapped[list["PositionSkill"]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )
    user_positions: Mapped[list["UserPosition"]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )

    @property
    def skills(self) -> list["Skill"]:
        """Compétences typiques du poste (aplatit la table de jonction)."""
        return [ps.skill for ps in self.position_skills]


class PositionSkill(Base):
    """Compétences typiques associées à un poste.
    Sert à pré-remplir les compétences d'un nouveau membre."""

    __tablename__ = "position_skills"

    position_id: Mapped[int] = mapped_column(
        ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )

    position: Mapped["Position"] = relationship(back_populates="position_skills")
    skill: Mapped["Skill"] = relationship(back_populates="position_skills")


# --------------------------------------------------------------------------- #
# Utilisateurs
# --------------------------------------------------------------------------- #

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)  # WhatsApp
    password_hash: Mapped[str] = mapped_column(String, nullable=False)  # Argon2

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    ownership_status: Mapped[OwnershipStatus] = mapped_column(
        default=OwnershipStatus.COLLABORATOR, nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Incrémenté à chaque changement/réinitialisation de mot de passe : révoque les jetons.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    employment_status: Mapped[str] = mapped_column(
        String(20), default="ACTIVE", server_default="ACTIVE", nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relations ---
    role: Mapped["Role"] = relationship(back_populates="users")
    user_positions: Mapped[list["UserPosition"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    user_skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    dev_membership: Mapped["DevMembership | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan",
        foreign_keys="DevMembership.user_id",
    )
    # Chat : relations inverses
    channel_members: Mapped[list["ChannelMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="user"
    )

    # --- Propriétés utilitaires ---
    @property
    def positions(self) -> list["Position"]:
        """Postes de l'utilisateur (aplatit la table de jonction)."""
        return [up.position for up in self.user_positions]

    @property
    def primary_position(self) -> "Position | None":
        """Poste principal (ou premier poste si aucun marqué principal)."""
        for up in self.user_positions:
            if up.is_primary:
                return up.position
        return self.positions[0] if self.user_positions else None

    @property
    def skills(self) -> list["Skill"]:
        """Compétences de l'utilisateur (aplatit la table de jonction user_skills)."""
        return [us.skill for us in self.user_skills]

    @property
    def permissions(self) -> set[str]:
        """Codes de permissions de l'utilisateur (via son rôle)."""
        return self.role.permission_codes


class UserPosition(Base):
    """Association utilisateur ↔ poste.
    Un utilisateur peut avoir plusieurs postes (principal + secondaires)."""

    __tablename__ = "user_positions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    position_id: Mapped[int] = mapped_column(
        ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="user_positions")
    position: Mapped["Position"] = relationship(back_populates="user_positions")


class UserSkill(Base):
    __tablename__ = "user_skills"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)

    user: Mapped["User"] = relationship(back_populates="user_skills")
    skill: Mapped["Skill"] = relationship(back_populates="user_skills")


# --------------------------------------------------------------------------- #
# Sécurité
# --------------------------------------------------------------------------- #

class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    old_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    """Lien de réinitialisation à usage unique ; seule l'empreinte SHA-256 est stockée."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
