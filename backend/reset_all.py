from app.database import SessionLocal, engine
from app.models import Request, Service
from sqlalchemy import inspect

db = SessionLocal()
insp = inspect(engine)

# Colonnes de la table requests
cols = [c["name"] for c in insp.get_columns("requests")]
print("=== Colonnes requests ===")
for c in ["reference", "agreed_amount", "currency", "event_date", "event_location"]:
    status = "OK" if c in cols else "MANQUANT"
    print(f"  {c}: {status}")

# Colonnes de la table services
cols_s = [c["name"] for c in insp.get_columns("services")]
print()
print("=== Colonnes services ===")
status = "OK" if "price_type" in cols_s else "MANQUANT"
print(f"  price_type: {status}")

# Données
print()
print("=== Données ===")
print(f"Services: {db.query(Service).count()}")
print(f"Demandes: {db.query(Request).count()}")

db.close()