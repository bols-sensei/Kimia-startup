"""
Création automatique du premier CEO au démarrage de l'application.
Appelé depuis le lifespan de FastAPI.
"""

import os

from app.core.security import check_password_strength, hash_password
from app.database import SessionLocal
from app.models import OwnershipStatus, Role, User
from app import seeds


def _create_first_admin_if_needed() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("[SEED-ADMIN] Des utilisateurs existent déjà, création ignorée")
            return

        email = os.getenv("FIRST_ADMIN_EMAIL")
        password = os.getenv("FIRST_ADMIN_PASSWORD")
        name = os.getenv("FIRST_ADMIN_NAME", "CEO Kimia")

        if not email or not password:
            print("[SEED-ADMIN] ⚠️ FIRST_ADMIN_EMAIL ou FIRST_ADMIN_PASSWORD non défini → création ignorée")
            return

        try:
            check_password_strength(password)
        except ValueError as exc:
            print(f"[SEED-ADMIN] ❌ Mot de passe refusé : {exc}")
            return

        ceo_role = db.query(Role).filter(Role.name == "CEO").one_or_none()
        if ceo_role is None:
            print("[SEED-ADMIN] ❌ Rôle CEO introuvable — seeds.run() a-t-il bien tourné ?")
            return

        admin = User(
            name=name,
            email=email,
            phone=None,
            password_hash=hash_password(password),
            role_id=ceo_role.id,
            ownership_status=OwnershipStatus.COFOUNDER,
            is_active=True,
            employment_status="ACTIVE",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print(f"[SEED-ADMIN] ✅ Premier CEO créé : {email}")
        print("[SEED-ADMIN] ⚠️  Changez le mot de passe après la première connexion.")

    except Exception as exc:
        db.rollback()
        print(f"[SEED-ADMIN] ❌ Erreur : {exc}")
        raise
    finally:
        db.close()


def run() -> None:
    print("=" * 60)
    print("[SEED] Démarrage du seed Kimia")
    print("=" * 60)

    seeds.run()
    _create_first_admin_if_needed()

    print("=" * 60)
    print("[SEED] ✅ Terminé")
    print("=" * 60)