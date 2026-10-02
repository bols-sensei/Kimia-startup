"""Réinitialisation d'un mot de passe en ligne de commande (CEO verrouillé hors de l'application).

Usage : python -m app.reset_password --email ceo@exemple.com
Le mot de passe est saisi de façon masquée ; toutes les sessions existantes sont révoquées.
"""

import argparse
import getpass
import sys

from app.core.security import check_password_strength, hash_password
from app.database import SessionLocal
from app.models import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Réinitialiser un mot de passe Kimia")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).one_or_none()
        if user is None:
            print("Utilisateur introuvable.")
            return 1
        password = getpass.getpass("Nouveau mot de passe : ")
        if password != getpass.getpass("Confirmer : "):
            print("Les mots de passe ne correspondent pas.")
            return 1
        try:
            check_password_strength(password)
        except ValueError as exc:
            print(exc)
            return 1
        user.password_hash = hash_password(password)
        user.token_version += 1
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()
        print(f"Mot de passe mis à jour pour {user.email}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
