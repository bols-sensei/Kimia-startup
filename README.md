# Kimia

Application interne de gestion (PWA) + site public pour une entreprise créative.
Documentation détaillée du code : **docs/Kimia-Documentation.pdf**.

- **Backend** : FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, Argon2, JWT, WebSocket
- **Frontend** : HTML / CSS / JavaScript vanilla (pas de framework) ; `frontend/app` est une PWA, `frontend/public` ne l'est pas

## Démarrage

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                       # DATABASE_URL, SECRET_KEY (obligatoire en production)

alembic revision --autogenerate -m "initial schema"
alembic upgrade head
python -m app.seeds                        # rôles, permissions, catégories, compétences, plateformes
python -m app.create_user --name "Votre nom" --email vous@exemple.com --role CEO --cofounder
uvicorn app.main:app --reload              # API :8000 — documentation interactive sur /docs

cd ../frontend &&    python -m http.server 5500    
# site public  : http://localhost:5500/public/
# application  : http://localhost:5500/app/login.html
```

L'URL de l'API du frontend se règle dans `frontend/public/assets/js/config.js` et `frontend/app/assets/js/config.js`.

## Tests

```bash
cd backend && pip install -r requirements-dev.txt
DATABASE_URL="sqlite://" pytest -q         # 12 tests API (SQLite en mémoire)
```

## Ce qui reste à faire (détail en section 6 du PDF)

- Web Push côté serveur (abonnements + clés VAPID) ; le Service Worker est prêt à les afficher
- Notifications automatiques restantes (nouvelle demande, échéance proche, publication à valider…)
- Permissions pilotées par les tables `permissions` (les routes testent aujourd'hui le nom du rôle)
- Écriture dans `audit_logs`, écran d'administration du catalogue, limitation de débit sur login / demandes publiques
- Migration initiale Alembic à générer sur votre PostgreSQL (les tests tournent sur SQLite)

```
kimia
├─ backend
│  ├─ alembic
│  │  ├─ env.py
│  │  ├─ script.py.mako
│  │  └─ versions
│  │     ├─ 185e4d362a81_add_phone_to_users.py
│  │     ├─ 2eaf395a08e5_add_phone_to_users.py
│  │     ├─ 580727017d23_add_chat_tables.py
│  │     ├─ 6862a8d269f3_add_user_positions.py
│  │     ├─ 872272390752_add_user_positions.py
│  │     ├─ a021f4275673_add_positions_and_position_skills.py
│  │     ├─ a1aef567664a_add_price_type_agreed_amount_currency_.py
│  │     ├─ ad647d7d91fc_add_portfolio_items_table.py
│  │     └─ c258e0ab76cc_initial_schema.py
│  ├─ alembic.ini
│  ├─ app
│  │  ├─ config.py
│  │  ├─ core
│  │  │  ├─ deps.py
│  │  │  ├─ notifications.py
│  │  │  ├─ security.py
│  │  │  ├─ ws_manager.py
│  │  │  └─ __init__.py
│  │  ├─ create_user.py
│  │  ├─ database.py
│  │  ├─ main.py
│  │  ├─ models
│  │  │  ├─ auth.py
│  │  │  ├─ business.py
│  │  │  ├─ chat.py
│  │  │  ├─ content.py
│  │  │  ├─ finance.py
│  │  │  ├─ workflow.py
│  │  │  └─ __init__.py
│  │  ├─ routers
│  │  │  ├─ activities.py
│  │  │  ├─ auth.py
│  │  │  ├─ chat.py
│  │  │  ├─ clients.py
│  │  │  ├─ cron.py
│  │  │  ├─ documents.py
│  │  │  ├─ finance.py
│  │  │  ├─ notifications.py
│  │  │  ├─ portfolio.py
│  │  │  ├─ positions.py
│  │  │  ├─ projects.py
│  │  │  ├─ public.py
│  │  │  ├─ publications.py
│  │  │  ├─ requests.py
│  │  │  ├─ security.py
│  │  │  ├─ services.py
│  │  │  ├─ skills.py
│  │  │  ├─ users.py
│  │  │  ├─ ws.py
│  │  │  └─ __init__.py
│  │  ├─ schemas
│  │  │  ├─ auth.py
│  │  │  ├─ business.py
│  │  │  ├─ chat.py
│  │  │  ├─ content.py
│  │  │  ├─ finance.py
│  │  │  ├─ workflow.py
│  │  │  └─ __init__.py
│  │  ├─ seeds.py
│  │  ├─ services
│  │  │  ├─ project_service.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ requirements-dev.txt
│  ├─ requirements.txt
│  ├─ reset_all.py
│  └─ tests
│     ├─ conftest.py
│     ├─ test_api.py
│     └─ __init__.py
├─ backend.zip
├─ docs
│  └─ Kimia-Documentation.pdf
├─ frontend
│  ├─ app
│  │  ├─ assets
│  │  │  ├─ css
│  │  │  │  └─ app.css
│  │  │  ├─ icons
│  │  │  │  └─ icon.svg
│  │  │  └─ js
│  │  │     ├─ main.js
│  │  │     └─ pages
│  │  │        ├─ activities.js
│  │  │        ├─ chat.js
│  │  │        ├─ clients.js
│  │  │        ├─ dashboard.js
│  │  │        ├─ documents.js
│  │  │        ├─ finances.js
│  │  │        ├─ notifications.js
│  │  │        ├─ planning.js
│  │  │        ├─ portfolio.js
│  │  │        ├─ projects.js
│  │  │        ├─ publications.js
│  │  │        ├─ requests.js
│  │  │        ├─ security.js
│  │  │        ├─ services.js
│  │  │        └─ team.js
│  │  ├─ components
│  │  │  └─ shell.js
│  │  ├─ index.html
│  │  ├─ login.html
│  │  ├─ manifest.json
│  │  ├─ offline.html
│  │  ├─ services
│  │  │  ├─ api.js
│  │  │  └─ websocket.js
│  │  ├─ state
│  │  │  └─ store.js
│  │  ├─ sw.js
│  │  └─ utils
│  │     └─ ui.js
│  ├─ assets
│  │  └─ js
│  │     └─ config.js
│  └─ public
│     ├─ assets
│     │  ├─ css
│     │  │  └─ public.css
│     │  ├─ icons
│     │  │  └─ icon.svg
│     │  └─ js
│     │     ├─ api.js
│     │     ├─ public.js
│     │     └─ ui.js
│     └─ index.html
└─ README.md

```