"""Caisse, rôles dynamiques, limite de comptes caisse, espace dev."""
import pytest

from app.core.access import CASHIER_PERMISSIONS
from app.core.security import hash_password
from app.models import DevMembership, Permission, Role, RolePermission, User
from tests.conftest import login


def auth(client, email="ceo@kimia.example.com"):
    return {"Authorization": f"Bearer {login(client, email).json()['access_token']}"}


@pytest.fixture()
def cashier(db):
    role = Role(name="CAISSIER")
    db.add(role)
    db.flush()
    for code in CASHIER_PERMISSIONS:
        p = db.query(Permission).filter_by(code=code).one_or_none()
        if p is None:
            p = Permission(code=code)
            db.add(p)
            db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=p.id))
    db.add(User(name="Caissier", email="cash@kimia.example.com", password_hash=hash_password("secret123"), role_id=role.id))
    db.commit()
    return role


def test_ceo_sees_cash_but_cannot_write(client, cashier):
    h = auth(client)
    assert client.get("/api/cash/balance", headers=h).status_code == 200
    assert client.get("/api/cash/audit", headers=h).status_code == 200
    r = client.post("/api/cash/transactions", headers=h, json={"direction": "IN", "amount": "10", "label": "Test"})
    assert r.status_code == 403
    assert client.post("/api/cash/closings", headers=h, json={}).status_code == 403


def test_cm_has_no_cash_access(client):
    assert client.get("/api/cash/balance", headers=auth(client, "cm@kimia.example.com")).status_code == 403


def test_cashier_flow_reversal_and_closing(client, cashier):
    hc, hceo = auth(client, "cash@kimia.example.com"), auth(client)
    tx = client.post("/api/cash/transactions", headers=hc, json={"direction": "IN", "amount": "500", "label": "Acompte mariage"})
    assert tx.status_code == 201 and tx.json()["reference"].startswith("CAI-")
    out = client.post("/api/cash/transactions", headers=hc, json={"direction": "OUT", "amount": "120.50", "label": "Transport"}).json()
    assert client.post("/api/cash/transactions", headers=hc, json={"direction": "IN", "amount": "-5", "label": "Négatif"}).status_code == 422

    # pas de modification ni suppression possibles
    assert client.patch(f"/api/cash/transactions/{out['id']}", headers=hc, json={"amount": "1"}).status_code in (404, 405)
    assert client.delete(f"/api/cash/transactions/{out['id']}", headers=hc).status_code in (404, 405)

    # annulation par écriture inverse, une seule fois
    assert client.post(f"/api/cash/transactions/{out['id']}/reverse", headers=hc, json={"reason": "x"}).status_code == 422
    rev = client.post(f"/api/cash/transactions/{out['id']}/reverse", headers=hc, json={"reason": "Erreur de saisie"})
    assert rev.status_code == 201 and rev.json()["direction"] == "IN" and rev.json()["reversal_of_id"] == out["id"]
    assert client.post(f"/api/cash/transactions/{out['id']}/reverse", headers=hc, json={"reason": "Encore"}).status_code == 409
    assert client.post(f"/api/cash/transactions/{rev.json()['id']}/reverse", headers=hc, json={"reason": "Annuler l'annulation"}).status_code == 409

    assert float(client.get("/api/cash/balance", headers=hceo).json()["balance"]) == 500.0

    closing = client.post("/api/cash/closings", headers=hc, json={"counted_balance": "495"})
    assert closing.status_code == 201
    assert float(closing.json()["closing_balance"]) == 500.0 and float(closing.json()["difference"]) == -5.0
    assert client.post("/api/cash/closings", headers=hc, json={}).status_code == 409
    assert client.post("/api/cash/transactions", headers=hc, json={"direction": "IN", "amount": "1", "label": "Après clôture"}).status_code == 409

    txs = client.get("/api/cash/transactions", headers=hceo).json()
    assert all(t["status"] == "CLOTUREE" for t in txs)
    audit = client.get("/api/cash/audit", headers=hceo).json()
    assert {a["action"] for a in audit} >= {"cash.transaction.created", "cash.transaction.reversed", "cash.closed"}
    assert client.get("/api/cash/transactions/export.csv", headers=hceo).status_code == 200


def test_only_one_cash_account_allowed(client, cashier):
    h = auth(client)
    r = client.post("/api/users", headers=h, json={
        "name": "Second", "email": "cash2@kimia.example.com", "phone": "+243000000",
        "password": "Secret12345", "role_id": cashier.id,
    })
    assert r.status_code == 409
    # un rôle non-caisse reste créable
    cm = client.get("/api/users/roles", headers=h).json()
    cm_id = next(x["id"] for x in cm if x["name"] == "CM")
    assert client.post("/api/users", headers=h, json={
        "name": "Autre", "email": "x@kimia.example.com", "phone": "+243111", "password": "Secret12345", "role_id": cm_id,
    }).status_code == 201


def test_custom_role_and_wildcard_protection(client):
    h = auth(client)
    r = client.post("/api/access/roles", headers=h, json={"name": "Chef de projet", "permission_codes": ["team.view", "dev.view"]})
    assert r.status_code == 201 and r.json()["name"] == "CHEF_DE_PROJET"
    rid = r.json()["id"]
    assert client.put(f"/api/access/roles/{rid}/permissions", headers=h, json={"permission_codes": ["*"]}).status_code == 400
    assert client.put(f"/api/access/roles/{rid}/permissions", headers=h, json={"permission_codes": ["nope.nope"]}).status_code == 400
    roles = client.get("/api/access/roles", headers=h).json()
    ceo = next(x for x in roles if x["name"] == "CEO")
    assert client.put(f"/api/access/roles/{ceo['id']}/permissions", headers=h, json={"permission_codes": []}).status_code == 403
    # accorder la caisse en écriture à un 2e rôle puis l'affecter dépasse la limite
    assert client.put(f"/api/access/roles/{rid}/permissions", headers=h, json={"permission_codes": ["cash.view"]}).status_code == 200
    assert client.get("/api/access/me", headers=auth(client, "cm@kimia.example.com")).json()["modules"]["cash"]["create"] is False
    me = client.get("/api/access/me", headers=h).json()
    assert me["modules"]["cash"]["view"] is True and me["modules"]["cash"]["create"] is False


def test_dev_members_vs_internal(client, db):
    h, hcm = auth(client), auth(client, "cm@kimia.example.com")
    cm = db.query(User).filter_by(email="cm@kimia.example.com").one()
    assert client.get("/api/dev/tools", headers=h).status_code == 403   # CEO sans DevMembership INTERNAL
    assert client.get("/api/dev/members", headers=hcm).status_code == 403
    r = client.put(f"/api/dev/members/{cm.id}", headers=h, json={"level": "MEMBER"})
    assert r.status_code == 200 and r.json()["level"] == "MEMBER"
    assert client.get("/api/dev/members", headers=h).status_code == 200
    ceo = db.query(User).filter_by(email="ceo@kimia.example.com").one()
    assert client.put(f"/api/dev/members/{ceo.id}", headers=h, json={"level": "INTERNAL"}).status_code == 200
    assert client.get("/api/dev/tools", headers=h).status_code == 200


def test_cannot_change_own_role_and_left_status(client, db):
    h = auth(client)
    ceo = db.query(User).filter_by(email="ceo@kimia.example.com").one()
    cm = db.query(User).filter_by(email="cm@kimia.example.com").one()
    assert client.patch(f"/api/users/{ceo.id}", headers=h, json={"employment_status": "LEFT"}).status_code == 400
    r = client.patch(f"/api/users/{cm.id}", headers=h, json={"employment_status": "LEFT"})
    assert r.status_code == 200 and r.json()["is_active"] is False and r.json()["employment_status"] == "LEFT"


def _project_service(client, h, amount="500"):
    sid = client.get("/api/public/services").json()[0]["id"]
    p = client.post("/api/projects", headers=h, json={
        "name": "Mariage", "project_type": "INTERNE", "category": "AUTRE",
        "services": [{"service_id": sid, "agreed_amount": amount}],
    }).json()
    return p["project_services"][0]["id"]


def test_cash_receipt_creates_payment_and_reversal_voids_it(client, cashier):
    hceo, hc = auth(client), auth(client, "cash@kimia.example.com")
    ps = _project_service(client, hceo)
    cur = client.get(f"/api/finance/project-services/{ps}/balance", headers=hceo).json()
    assert float(cur["total_paid"]) == 0

    tx = client.post("/api/cash/transactions", headers=hc, json={
        "direction": "IN", "amount": "300", "label": "Acompte", "project_service_id": ps}).json()
    bal = client.get(f"/api/finance/project-services/{ps}/balance", headers=hceo).json()
    assert float(bal["total_paid"]) == 300 and float(bal["remaining"]) == 200
    detail = client.get(f"/api/finance/project-services/{ps}/detail", headers=hceo).json()
    pay = detail["revenues"][0]["payments"][0]
    assert pay["cash_transaction_id"] == tx["id"] and pay["voided_at"] is None

    # dépassement du reste à payer refusé, devise différente refusée
    assert client.post("/api/cash/transactions", headers=hc, json={
        "direction": "IN", "amount": "300", "label": "Trop", "project_service_id": ps}).status_code == 409
    assert client.post("/api/cash/transactions", headers=hc, json={
        "direction": "IN", "amount": "10", "label": "Autre devise", "currency": "EUR",
        "project_service_id": ps}).status_code == 400

    # annulation de caisse : le paiement est annulé (conservé), le solde revient
    assert client.post(f"/api/cash/transactions/{tx['id']}/reverse", headers=hc, json={"reason": "Erreur de montant"}).status_code == 201
    bal = client.get(f"/api/finance/project-services/{ps}/balance", headers=hceo).json()
    assert float(bal["total_paid"]) == 0 and float(bal["remaining"]) == 500
    detail = client.get(f"/api/finance/project-services/{ps}/detail", headers=hceo).json()
    assert detail["revenues"][0]["payments"][0]["voided_at"] is not None
    actions = {a["action"] for a in client.get("/api/cash/audit", headers=hceo).json()}
    assert "cash.transaction.created" in actions


def test_cash_expense_and_reversal_of_expense_do_not_create_payments(client, cashier):
    hceo, hc = auth(client), auth(client, "cash@kimia.example.com")
    ps = _project_service(client, hceo)
    out = client.post("/api/cash/transactions", headers=hc, json={
        "direction": "OUT", "amount": "50", "label": "Location matériel", "project_service_id": ps}).json()
    client.post(f"/api/cash/transactions/{out['id']}/reverse", headers=hc, json={"reason": "Erreur de saisie"})
    bal = client.get(f"/api/finance/project-services/{ps}/balance", headers=hceo).json()
    assert float(bal["total_paid"]) == 0
    assert client.get(f"/api/finance/project-services/{ps}/detail", headers=hceo).json()["revenues"] == []


def test_receivables_lists_open_project_services_for_cashier(client, cashier):
    hceo, hc = auth(client), auth(client, "cash@kimia.example.com")
    ps = _project_service(client, hceo, "500")
    assert client.get("/api/cash/receivables", headers=hceo).status_code == 403   # CEO : lecture seule
    rows = client.get("/api/cash/receivables", headers=hc).json()
    row = next(r for r in rows if r["project_service_id"] == ps)
    assert float(row["remaining"]) == 500 and " — " in row["label"]
    client.post("/api/cash/transactions", headers=hc, json={
        "direction": "IN", "amount": "500", "label": "Solde", "project_service_id": ps})
    assert all(r["project_service_id"] != ps for r in client.get("/api/cash/receivables", headers=hc).json())
