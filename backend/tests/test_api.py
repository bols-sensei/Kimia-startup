from tests.conftest import login


def auth(client, email="ceo@kimia.example.com"):
    token = login(client, email).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_ok_and_me(client):
    r = login(client)
    assert r.status_code == 200
    assert "password_hash" not in r.text
    me = client.get("/api/auth/me", headers=auth(client))
    assert me.json()["role"]["name"] == "CEO"


def test_account_locks_after_failed_attempts(client):
    for _ in range(5):
        assert login(client, password="bad").status_code == 401
    assert login(client).status_code == 403  # bon mot de passe mais compte bloqué


def test_cm_cannot_access_finance_or_clients(client):
    h = auth(client, "cm@kimia.example.com")
    assert client.get("/api/clients", headers=h).status_code == 403
    assert client.post("/api/finance/revenues", headers=h, json={"project_service_id": 1, "amount": 10}).status_code == 403


def test_no_token_is_401(client):
    assert client.get("/api/projects").status_code == 401


def test_public_request_workflow_and_project_generation(client):
    services = client.get("/api/public/services").json()
    sid = services[0]["id"]
    r = client.post("/api/public/requests", json={
        "client_name": "Sarah", "client_phone": "+22500000000",
        "service_id": sid, "form_data": {"lieu": "Abidjan"},
    })
    assert r.status_code == 201
    rid = r.json()["id"]
    h = auth(client)

    # transition invalide (NOUVELLE -> CONFIRMEE)
    bad = client.patch(f"/api/requests/{rid}/status", headers=h, json={"new_status": "CONFIRMEE"})
    assert bad.status_code == 400
    for s in ["A_CONTACTER", "EN_DISCUSSION", "CONFIRMEE"]:
        assert client.patch(f"/api/requests/{rid}/status", headers=h, json={"new_status": s}).status_code == 200
    assert len(client.get(f"/api/requests/{rid}/history", headers=h).json()) == 3

    req = client.get(f"/api/requests/{rid}", headers=h).json()
    p = client.post("/api/projects", headers=h, json={
        "client_id": req["client_id"], "request_id": rid, "name": "Mariage Sarah",
        "project_type": "CLIENT", "category": "PHOTOGRAPHIE",
        "services": [{"service_id": sid, "agreed_amount": "500"}],
    })
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    acts = client.get(f"/api/activities?project_id={pid}", headers=h).json()
    assert len(acts) == 1 and acts[0]["template_id"] is not None
    detail = client.get(f"/api/activities/{acts[0]['id']}", headers=h).json()
    assert len(detail["checklist_items"]) == 2


def test_finance_balance_partial_payments(client):
    h = auth(client)
    sid = client.get("/api/public/services").json()[0]["id"]
    p = client.post("/api/projects", headers=h, json={
        "name": "Interne", "project_type": "INTERNE", "category": "AUTRE",
        "services": [{"service_id": sid, "agreed_amount": "500"}],
    }).json()
    ps = p["project_services"][0]["id"]
    # Les écritures de finance sont réservées au rôle comptable (jamais au CEO)
    hf = auth(client, "compta@kimia.example.com")
    assert client.post("/api/finance/revenues", headers=h, json={"project_service_id": ps, "amount": "500"}).status_code == 403
    rev = client.post("/api/finance/revenues", headers=hf, json={"project_service_id": ps, "amount": "500"}).json()
    for amt in ("300", "200"):
        assert client.post("/api/finance/payments", headers=hf, json={
            "revenue_id": rev["id"], "amount": amt, "paid_at": "2026-09-01T10:00:00Z"}).status_code == 201
    assert client.post("/api/finance/payments", headers=h, json={
        "revenue_id": rev["id"], "amount": "1", "paid_at": "2026-09-01T10:00:00Z"}).status_code == 403
    client.post("/api/finance/remunerations", headers=hf, json={"project_service_id": ps, "user_id": 1, "amount": "150"})
    # Le CEO garde la lecture complète
    b = client.get(f"/api/finance/project-services/{ps}/balance", headers=h).json()
    assert float(b["total_paid"]) == 500 and float(b["remaining"]) == 0 and float(b["total_remunerated"]) == 150
    assert client.get(f"/api/finance/project-services/{ps}/detail", headers=auth(client, "cm@kimia.example.com")).status_code == 403


def test_cm_only_edits_assigned_activity(client):
    h = auth(client)
    sid = client.get("/api/public/services").json()[0]["id"]
    p = client.post("/api/projects", headers=h, json={
        "name": "P", "project_type": "INTERNE", "category": "AUTRE",
        "services": [{"service_id": sid, "agreed_amount": "1"}]}).json()
    aid = client.get(f"/api/activities?project_id={p['id']}", headers=h).json()[0]["id"]
    hcm = auth(client, "cm@kimia.example.com")
    assert client.patch(f"/api/activities/{aid}", headers=hcm, json={"status": "EN_COURS"}).status_code == 403
    client.post(f"/api/activities/{aid}/assignments", headers=h, json={"user_id": 2, "assignment_role": "PARTICIPANT"})
    assert client.patch(f"/api/activities/{aid}", headers=hcm, json={"status": "EN_COURS"}).status_code == 200
    assert len(client.get("/api/notifications", headers=hcm).json()) == 1


def test_security_endpoints_ceo_only(client):
    login(client, password="bad")
    h = auth(client)
    ev = client.get("/api/security/events", headers=h).json()["items"]  # réponse paginée
    assert any(e["success"] is False for e in ev)
    assert client.get("/api/security/events", headers=auth(client, "cm@kimia.example.com")).status_code == 403
    assert client.get("/api/users/team", headers=auth(client, "cm@kimia.example.com")).status_code == 403


def test_public_catalog_exposes_dynamic_form_fields(client):
    svc = client.get("/api/public/services").json()[0]
    assert svc["form_fields"][0]["form_field"]["label"] == "Lieu"
    assert svc["form_fields"][0]["is_required"] is True


def test_extras_platforms_roles_finance_detail_mine(client):
    h = auth(client)
    assert client.get("/api/users/roles", headers=h).status_code == 200
    team = client.get("/api/users/team", headers=h).json()
    assert "skills" in team[0] and "password_hash" not in str(team)
    assert client.get("/api/publications/platforms", headers=h).status_code == 200
    assert client.get("/api/activities?mine=true", headers=h).json() == []
    sid = client.get("/api/public/services").json()[0]["id"]
    p = client.post("/api/projects", headers=h, json={"name": "X", "project_type": "INTERNE", "category": "AUTRE",
        "services": [{"service_id": sid, "agreed_amount": "100"}]}).json()
    ps = p["project_services"][0]["id"]
    d = client.get(f"/api/finance/project-services/{ps}/detail", headers=h).json()
    assert d["revenues"] == [] and float(d["remaining"]) == 100


def test_publication_flow_roles(client, db):
    from app.models import Platform
    db.add(Platform(name="Instagram")); db.commit()
    hcm, hceo = auth(client, "cm@kimia.example.com"), auth(client)
    pub = client.post("/api/publications", headers=hcm, json={"title": "Reel", "platform_ids": [1]}).json()
    assert pub["platform_ids"] == [1] and pub["status"] == "BROUILLON"
    assert client.patch(f"/api/publications/{pub['id']}", headers=hcm, json={"status": "VALIDE"}).status_code == 403
    assert client.patch(f"/api/publications/{pub['id']}", headers=hcm, json={"status": "A_VALIDER"}).status_code == 200
    assert client.patch(f"/api/publications/{pub['id']}", headers=hceo, json={"status": "VALIDE"}).json()["status"] == "VALIDE"


def test_create_user_cli_helper(db):
    import pytest
    from app.core.security import verify_password
    from app.create_user import create_user
    u = create_user(db, name="Dora", email="da@kimia.example.com", password="longenough1", role_name="DA")
    assert u.role.name == "DA" and verify_password("longenough1", u.password_hash)
    with pytest.raises(ValueError):
        create_user(db, name="X", email="da@kimia.example.com", password="longenough1", role_name="DA")  # doublon
    with pytest.raises(ValueError):
        create_user(db, name="Y", email="y@kimia.example.com", password="short", role_name="DA")
    with pytest.raises(ValueError):
        create_user(db, name="Z", email="z@kimia.example.com", password="longenough1", role_name="INCONNU")
