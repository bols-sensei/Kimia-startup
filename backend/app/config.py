"""
Configuration de l'application.
Ne contient QUE de la configuration (env, JWT, paramètres métier).
"""

from functools import lru_cache
import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Base de données ---
    database_url: str = "postgresql+psycopg2://kimia:kimia@localhost:5432/kimia"

    # --- Environnement ---
    environment: str = "development"

    # --- Authentification / JWT ---
    secret_key: str = "CHANGE_ME_IN_PROD"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 24 * 60

    # --- Sécurité des comptes ---
    max_login_attempts: int = 5
    account_lock_minutes: int = 14

    # --- Protection par IP ---
    ip_max_failures: int = 20
    ip_forgot_max: int = 5
    ip_window_minutes: int = 15

    # --- Mots de passe ---
    min_password_length: int = 10
    password_reset_ttl_minutes: int = 30

    # --- Cron ---
    cron_secret: str = ""

    # --- Documents ---
    max_document_size_mb: int = 20

    # --- Caisse ---
    max_cash_operators: int = 1

    # --- Finance ---
    default_currency: str = "USD"

    # ------------------------------------------------------------------ #
    # Validateurs
    # ------------------------------------------------------------------ #

    @model_validator(mode="after")
    def _normalize_database_url(self):
        """Render fournit postgresql://, SQLAlchemy veut postgresql+psycopg2://"""
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://", "postgresql+psycopg2://", 1
            )
        return self

    @model_validator(mode="after")
    def _check_secrets(self):
        weak = self.secret_key == "CHANGE_ME_IN_PROD" or len(self.secret_key) < 32
        if self.environment.lower() == "production":
            if weak:
                raise ValueError("SECRET_KEY faible ou par défaut : 32 caractères aléatoires minimum en production")
            if len(self.cron_secret) < 24 or self.cron_secret == self.secret_key:
                raise ValueError("CRON_SECRET (24+ caractères, différent de SECRET_KEY) obligatoire en production")
        elif self.secret_key == "CHANGE_ME_IN_PROD":
            warnings.warn("SECRET_KEY par défaut : à changer avant toute mise en production", stacklevel=2)
        return self

    @property
    def max_document_size_bytes(self) -> int:
        return self.max_document_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()