"""
Configuration de l'application.
Ne contient QUE de la configuration (env, JWT, paramètres métier).
La connexion DB (engine/session/Base) vit dans database.py — voir §8 du brief.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Base de données ---
    database_url: str = "postgresql+psycopg2://kimia:kimia@localhost:5432/kimia"

    # --- Authentification / JWT ---
    secret_key: str = "CHANGE_ME_IN_PROD"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 24 * 60  # 24h, pas de refresh token (§19)

    # --- Sécurité des comptes (§20) ---
    max_login_attempts: int = 5
    account_lock_minutes: int = 14

    # --- Documents (§28) ---
    max_document_size_mb: int = 20

    @property
    def max_document_size_bytes(self) -> int:
        return self.max_document_size_mb * 1024 * 1024

    # --- Finance (§29) ---
    # Devise unique retenue : USD (dollar).
    default_currency: str = "USD"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()