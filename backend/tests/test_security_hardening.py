"""Points critiques : mot de passe, jetons révocables, reset par lien, limite IP, fichiers, cron, config."""
import pytest
from datetime import datetime, timedelta, timezone
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.models import PasswordResetToken
from tests.conftest import login

STRONG = "Nouveau12345"


def auth(client, email="ceo@kimia.example.com", password="secret123"):
    return {"Authorization": f"Bearer {login(client, email, password).json()['access_token']}"}


def uid(db, email):
    from app.models import User
    return db.query(User).filter_by(email=email).one().id


def test_password_policy_on_api(client):
    h = auth(client)
    role_id = client.get("/api/users/roles", headers=h).json()[0]["id"]
    for bad in ("court1", "uniquementdeslettres", "1234567890123"):
        r = client.post("/api/users", headers=h, json={
            "name": "X", "email": "x@kimia.example.com", "phone": "+243", "password": bad, "role_id": role_id})
        assert r.status_code == 422, bad


def test_reset_link_flow_and_token_revocation(client, db):
    hceo, hcm = auth(client), auth(client, "cm@kimia.example.com")
    assert client.get("/api/auth/me", headers=hcm).status_code == 200
    cm_id = uid(db, "cm@kimia.example.com")

    # Les non-autorisés ne peuvent pas générer de lien
    assert client.post(f"/api/users/{cm_id}/reset-link", headers=hcm).status_code == 403

    link = client.post(f"/api/users/{cm_id}/reset-link", headers=hceo).json()
    assert link["token"] in link["path"]

    # mot de passe faible : refusé SANS consommer le lien
    assert client.post("/api/auth/reset-password", json={"token": link["token"], "new_password": "faible"}).status_code == 422
    ok = client.post("/api/auth/reset-password", json={"token": link["token"], "new_password": STRONG})
    assert ok.status_code == 200

    # usage unique, ancien jeton révoqué, ancien mot de passe invalide, nouveau accepté
    assert client.post("/api/auth/reset-password", json={"token": link["token"], "new_password": STRONG}).status_code == 400
    assert client.get("/api/auth/me", headers=hcm).status_code == 401
    assert login(client, "cm@kimia.example.com", "secret123").status_code == 401
    assert login(client, "cm@kimia.example.com", STRONG).status_code == 200

    # l'intéressé est prévenu (lien généré, puis mot de passe modifié)
    types = {n["type"] for n in client.get("/api/notifications", headers=auth(client, "cm@kimia.example.com", STRONG)).json()}
    assert {"security.reset_link", "security.password_changed"} <= types


def test_reset_link_expires(client, db):
    hceo = auth(client)
    cm_id = uid(db, "cm@kimia.example.com")
    link = client.post(f"/api/users/{cm_id}/reset-link", headers=hceo).json()
    db.query(PasswordResetToken).update({"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)})
    db.commit()
    assert client.post("/api/auth/reset-password", json={"token": link["token"], "new_password": STRONG}).status_code == 400


def test_forgot_password_no_enumeration_notifies_ceo_and_is_throttled(client):
    a = client.post("/api/auth/forgot-password", json={"email": "inconnu@kimia.example.com"})
    b = client.post("/api/auth/forgot-password", json={"email": "cm@kimia.example.com"})
    assert a.status_code == b.status_code == 202 and a.json() == b.json()
    notifs = client.get("/api/notifications", headers=auth(client)).json()
    assert any(n["type"] == "password.reset_requested" for n in notifs)
    codes = [client.post("/api/auth/forgot-password", json={"email": "cm@kimia.example.com"}).status_code for _ in range(6)]
    assert 429 in codes


def test_change_password_revokes_old_token(client):
    old = auth(client, "cm@kimia.example.com")
    assert client.post("/api/auth/change-password", headers=old, json={
        "current_password": "mauvais", "new_password": STRONG}).status_code == 400
    r = client.post("/api/auth/change-password", headers=old, json={
        "current_password": "secret123", "new_password": STRONG})
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=old).status_code == 401
    new = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new).status_code == 200


def test_login_ip_throttle(client):
    codes = [client.post("/api/auth/login", json={"email": f"nobody{i}@kimia.example.com", "password": "x"}).status_code
             for i in range(22)]
    assert codes[0] == 401 and 429 in codes
    # même le bon mot de passe est refusé depuis cette IP tant que la fenêtre court
    assert client.post("/api/auth/login", json={"email": "ceo@kimia.example.com", "password": "secret123"}).status_code == 429


def test_websocket_rejects_revoked_token(client):
    old = login(client, "cm@kimia.example.com").json()["access_token"]
    with client.websocket_connect(f"/ws?token={old}") as ws:
        ws.send_text("ping")
    client.post("/api/auth/change-password", headers={"Authorization": f"Bearer {old}"},
                json={"current_password": "secret123", "new_password": STRONG})
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws?token={old}") as ws:
            ws.receive_text()
    assert exc.value.code == 4401


def test_sensitive_account_password_is_chosen_by_the_user(client, db):
    h = auth(client)
    role = client.post("/api/access/roles", headers=h, json={
        "name": "Caisse test", "permission_codes": ["cash.view", "cash.create"]}).json()
    r = client.post("/api/users", headers=h, json={
        "name": "Caissier2", "email": "c2@kimia.example.com", "phone": "+243", "password": "CeoLeConnait123",
        "role_id": role["id"]})
    assert r.status_code == 201 and r.headers["X-Password-Setup"] == "reset-link-required"
    # le mot de passe fourni par le CEO est ignoré
    assert login(client, "c2@kimia.example.com", "CeoLeConnait123").status_code == 401
    # et le CEO ne peut pas non plus en imposer un
    assert client.post(f"/api/users/{r.json()['id']}/reset-password", headers=h, json={"new_password": "Impose123456"}).status_code == 409
    link = client.post(f"/api/users/{r.json()['id']}/reset-link", headers=h).json()
    assert client.post("/api/auth/reset-password", json={"token": link["token"], "new_password": STRONG}).status_code == 200
    assert login(client, "c2@kimia.example.com", STRONG).status_code == 200


def test_permission_based_routes_for_custom_role(client):
    h = auth(client)
    role = client.post("/api/access/roles", headers=h, json={"name": "Lecteur", "permission_codes": ["clients.view"]}).json()
    client.post("/api/users", headers=h, json={
        "name": "Lecteur", "email": "l@kimia.example.com", "phone": "+243", "password": STRONG, "role_id": role["id"]})
    hl = auth(client, "l@kimia.example.com", STRONG)
    assert client.get("/api/clients", headers=hl).status_code == 200
    assert client.post("/api/clients", headers=hl, json={"name": "X", "email": "c@x.com"}).status_code == 403
    assert client.get("/api/requests", headers=hl).status_code == 403
    assert client.get("/api/security/events", headers=hl).status_code == 403


def _project_id(client, h):
    sid = client.get("/api/public/services").json()[0]["id"]
    return client.post("/api/projects", headers=h, json={
        "name": "P", "project_type": "INTERNE", "category": "AUTRE",
        "services": [{"service_id": sid, "agreed_amount": "100"}]}).json()["id"]


def test_document_upload_validation(client):
    h = auth(client)
    pid = _project_id(client, h)
    up = lambda name, data: client.post(f"/api/documents?project_id={pid}", headers=h, files={"file": (name, data, "text/html")})
    assert up("evil.html", b"<script>1</script>").status_code == 415
    assert up("run.exe", b"MZ").status_code == 415
    assert up("fake.pdf", b"<html>").status_code == 415          # signature ≠ extension
    assert client.post("/api/documents?project_id=99999", headers=h, files={"file": ("a.pdf", b"%PDF-1.4", "x")}).status_code == 404
    ok = up("../../contrat.pdf", b"%PDF-1.4 contenu")
    assert ok.status_code == 201
    body = ok.json()
    assert body["name"] == "contrat.pdf" and body["mime_type"] == "application/pdf"
    assert ".." not in body["path"] and "contrat" not in body["path"]


def test_portfolio_rejects_svg_and_fake_images(client):
    h = auth(client)
    svg = client.post("/api/portfolio/upload", headers=h, files={"file": ("x.svg", b"<svg onload=alert(1)>", "image/svg+xml")})
    assert svg.status_code == 400
    fake = client.post("/api/portfolio/upload", headers=h, files={"file": ("x.html", b"<html>", "image/png")})
    assert fake.status_code == 400
    png = client.post("/api/portfolio/upload", headers=h, files={"file": ("x.html", b"\x89PNG\r\n\x1a\n0000", "image/png")})
    assert png.status_code == 200 and png.json()["image_path"].endswith(".png")


def test_cron_secret_constant_time_and_required(client):
    assert client.post("/api/cron/check-deadlines").status_code == 403
    assert client.post("/api/cron/check-deadlines", headers={"X-Cron-Secret": "faux"}).status_code == 403


def test_production_refuses_weak_secrets():
    with pytest.raises(ValueError):
        Settings(environment="production", secret_key="CHANGE_ME_IN_PROD", cron_secret="c" * 30,
                 database_url="sqlite://")
    with pytest.raises(ValueError):
        Settings(environment="production", secret_key="s" * 40, cron_secret="", database_url="sqlite://")
    assert Settings(environment="production", secret_key="s" * 40, cron_secret="c" * 30, database_url="sqlite://")
