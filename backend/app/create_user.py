"""
Création du premier compte (ou de tout compte) en ligne de commande.

Il n'y a volontairement aucune inscription publique : le premier CEO se crée ici,
les suivants depuis la page « Équipe » de l'application.

    python -m app.create_user --name "Ruben" --email ceo@exemple.com --role CEO --cofounder
(le mot de passe est demandé de façon masquée)
"""

import argparse
import getpass
import sys

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import OwnershipStatus, Role, User


def create_user(db: Session, *, name: str, email: str, password: str, role_name: str,
                ownership: OwnershipStatus = OwnershipStatus.COLLABORATOR) -> User:
    role = db.query(Role).filter(Role.name == role_name).one_or_none()
    if role is None:
        raise ValueError(f"Rôle « {role_name} » introuvable — lancez d'abord `python -m app.seeds`.")
    if db.query(User).filter(User.email == email).one_or_none():
        raise ValueError(f"Un compte existe déjà pour {email}.")
    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
    user = User(name=name, email=email, password_hash=hash_password(password), role_id=role.id, ownership_status=ownership)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> int:
    ap = argparse.ArgumentParser(description="Créer un utilisateur Kimia")
    ap.add_argument("--name", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--role", required=True, help="CEO, DA ou CM")
    ap.add_argument("--cofounder", action="store_true", help="statut cofondateur (sinon collaborateur)")
    args = ap.parse_args()

    password = getpass.getpass("Mot de passe : ")
    if password != getpass.getpass("Confirmez : "):
        print("Les mots de passe ne correspondent pas.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = create_user(db, name=args.name, email=args.email, password=password, role_name=args.role,
                           ownership=OwnershipStatus.COFOUNDER if args.cofounder else OwnershipStatus.COLLABORATOR)
        print(f"Compte créé : {user.email} ({args.role})")
        return 0
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
