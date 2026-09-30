"""Fixtures de test : SQLite en mémoire (types PostgreSQL INET/JSONB émulés)."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@compiles(INET, "sqlite")
def _inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


@compiles(JSONB, "sqlite")
def _jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models import (
    ActivityTemplate, Category, ChecklistTemplateItem, FormField, Role, Service, ServiceFormField, Skill, User,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()

    ceo_role, da_role, cm_role = Role(name="CEO"), Role(name="DA"), Role(name="CM")
    session.add_all([ceo_role, da_role, cm_role])
    session.flush()
    session.add_all([
        User(name="Ruben", email="ceo@kimia.example.com", password_hash=hash_password("secret123"), role_id=ceo_role.id),
        User(name="CM", email="cm@kimia.example.com", password_hash=hash_password("secret123"), role_id=cm_role.id),
    ])
    cat = Category(name="Photographie")
    skill = Skill(name="Photography")
    session.add_all([cat, skill])
    session.flush()
    svc = Service(category_id=cat.id, name="Photographie de mariages")
    session.add(svc)
    session.flush()
    tpl = ActivityTemplate(service_id=svc.id, name="Préparer matériel", required_skill_id=skill.id)
    session.add(tpl)
    session.flush()
    session.add_all([
        ChecklistTemplateItem(activity_template_id=tpl.id, label="Batteries", display_order=1),
        ChecklistTemplateItem(activity_template_id=tpl.id, label="Cartes SD", display_order=2),
    ])
    ff = FormField(label="Lieu", field_type="text")
    session.add(ff)
    session.flush()
    session.add(ServiceFormField(service_id=svc.id, form_field_id=ff.id, display_order=1, is_required=True))
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: (yield db)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, email="ceo@kimia.example.com", password="secret123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    return r
