"""
Connexion PostgreSQL : engine, session, Base déclarative, dépendance get_db().
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # détecte les connexions mortes
    pool_size=5,             # connexions persistantes
    max_overflow=5,          # connexions temporaires
    pool_recycle=300,        # recycle après 5 min (Render ferme à 5 min)
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles SQLAlchemy."""
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()