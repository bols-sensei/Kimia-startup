"""
Argon2 pour les mots de passe, JWT pour l'authentification.
Payload minimal : sub (user_id), role, iat, exp — §19 du brief.
Aucune notion de refresh token (durée de vie fixe 24h).
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.config import settings

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(*, user_id: int, role: str, token_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "role": role, "tv": token_version, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None



# --------------------------------------------------------------------------- #
# Révocation : `tv` (token_version) du JWT doit égaler users.token_version.
# Incrémenter users.token_version invalide tous les jetons déjà émis.
# --------------------------------------------------------------------------- #

def new_reset_token() -> tuple[str, str]:
    """Retourne (jeton_en_clair, empreinte). Seule l'empreinte est stockée."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def check_password_strength(password: str) -> str:
    """Valide la robustesse minimale ; lève ValueError (message en français)."""
    if len(password) < settings.min_password_length:
        raise ValueError(f"Le mot de passe doit contenir au moins {settings.min_password_length} caractères")
    if len(password) > 128:
        raise ValueError("Le mot de passe est trop long (128 caractères maximum)")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Le mot de passe doit contenir au moins une lettre et un chiffre")
    if len(set(password)) < 5:
        raise ValueError("Le mot de passe est trop répétitif")
    return password
