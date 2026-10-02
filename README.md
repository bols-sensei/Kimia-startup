# Kimia — État du projet (1er octobre 2026)

Application interne de gestion pour l'agence créative Kimia : demandes clients, projets, prestations, activités, planning, publications, documents, chat, finance et **caisse**.

- **Backend** : FastAPI + SQLAlchemy 2 + PostgreSQL, migrations Alembic, auth JWT (Argon2)
- **Frontend** : PWA en JavaScript natif (`frontend/app`) + site public (`frontend/public`), servis par FastAPI
- **Temps réel** : WebSocket (`/ws`) pour notifications et mises à jour d'écrans
- **Tests** : `pytest` sur SQLite en mémoire — **21 tests, tous verts**

> Le frontend n'a **pas** encore été adapté aux nouveautés de ce document (caisse, rôles dynamiques, équipe dev, statut professionnel).

---

## 1. Structure

```
backend/
  app/
    main.py            montage des routeurs + fichiers statiques
    config.py          paramètres (.env)
    database.py        engine / session / Base
    seeds.py           rôles, permissions, catalogue, postes, compétences
    create_user.py     création du premier compte (CLI)
    core/
      deps.py          get_current_user, require_permission, require_dev_internal
      access.py        catalogue de permissions + règle du joker "*"
      audit.py         écriture dans audit_logs
      cash_guard.py    limite du nombre de comptes « caisse »
      notifications.py / ws_manager.py / security.py
    models/            auth, business, workflow, content, finance, chat, cash, dev
    schemas/           Pydantic (auth, access, cash, finance, workflow, …)
    routers/           un fichier par domaine (voir §4)
  alembic/versions/    9 migrations, chaîne linéaire (tête : c9d8e7f6a5b4)
  tests/               test_api.py, test_cash_access.py
frontend/
  app/                 PWA (pages : dashboard, requests, projects, activities,
                       planning, publications, documents, finances, team,
                       security, services, portfolio, chat, notifications, clients)
  public/              site vitrine + formulaire de demande
```

## 2. Lancer le projet

```bash
cd backend
pip install -r requirements.txt            # + requirements-dev.txt pour les tests
# .env : DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
#        MAX_LOGIN_ATTEMPTS, ACCOUNT_LOCK_MINUTES, MAX_DOCUMENT_SIZE_MB, DEFAULT_CURRENCY
alembic upgrade head                        # applique toutes les migrations
python -m app.seeds                         # rôles, permissions, catalogue (idempotent)
python -m app.create_user --name "…" --email … --role CEO --cofounder
uvicorn app.main:app --reload               # API : /docs — App : /app — Public : /public
python -m pytest -q                         # tests
```

Variables optionnelles : `MAX_CASH_OPERATORS` (défaut `1`).

## 3. Modèle d'accès

Le principe : **le code fournit le moteur, les données configurent l'entreprise.**

```
USER ── ROLE ── PERMISSIONS        (ce que la personne peut faire)
  ├──── POSITIONS ── COMPÉTENCES   (ce que la personne sait faire)
  ├──── DEV MEMBERSHIP             (membre dev / dev interne)
  └──── ownership_status           (cofondateur / collaborateur : informatif)
```

- Les **rôles sont des lignes en base** (`roles`), pas un enum. Rôles seedés : `CEO`, `DA`, `CM`, `CAISSIER`, `COMPTABLE`.
- `ownership_status` n'accorde **aucun droit** ; seuls rôle → permissions comptent.
- **Joker `*` (CEO)** : tous les droits de lecture et d'administration, **sauf** les écritures de caisse (`cash.create`, `cash.cancel`, `cash.close`, `cash.reconcile`) et les écritures de finance (`finance.manage`). Ces permissions doivent être accordées explicitement à un rôle (voir `core/access.py`).
- Statut professionnel (`employment_status`) : `ACTIVE`, `ABSENT`, `LEAVE`, `SUSPENDED`, `LEFT`, distinct de `is_active` (accès au compte). `LEFT` désactive le compte mais conserve l'historique. Aucun membre n'est supprimé physiquement (soft delete).
- Le CEO ne peut pas modifier son propre rôle, son statut ou se bloquer lui-même.

### Permissions du catalogue (nouvelles)

| Module | Codes |
|---|---|
| Caisse | `cash.view`, `cash.create`, `cash.cancel`, `cash.close`, `cash.reconcile`, `cash.audit`, `cash.export` |
| Finance | `finance.view`, `finance.manage` |
| Équipe / rôles | `team.view`, `team.manage`, `team.skills`, `roles.manage` |
| Développement | `dev.view`, `dev.manage`, `dev.tools.use` |

Rôle `COMPTABLE` seedé : `dashboard.view`, `notifications.view`, `finance.view`, `finance.manage`.

Rôle `CAISSIER` seedé : `dashboard.view`, `notifications.view`, `cash.view`, `cash.create`, `cash.cancel`, `cash.close`, `cash.export`.

## 4. API (≈ 100 routes)

| Domaine | Préfixe | Notes |
|---|---|---|
| Auth | `/api/auth` | login, `me`, déblocage de compte. Verrouillage après 5 échecs. |
| Membres | `/api/users` | team, CRUD, compétences, reset mot de passe, toggle actif, soft delete |
| Postes / compétences | `/api/positions`, `/api/skills` | configurables en base |
| Clients, demandes, projets | `/api/clients`, `/api/requests`, `/api/projects` | workflow de statuts des demandes, génération de projet |
| Activités | `/api/activities` | templates, checklists, affectations, suggestions par compétence |
| Planning / publications / documents | `/api/publications`, `/api/documents` | upload dans `storage/documents` |
| Finance (MVP) | `/api/finance` | lecture : `finance.view` (CEO inclus) ; écriture (revenus, paiements, rémunérations) : `finance.manage`, **jamais le CEO** — rôle `COMPTABLE` |
| **Caisse** | `/api/cash` | **nouveau** — voir §5 |
| **Rôles & accès** | `/api/access` | **nouveau** — permissions, rôles, `me` (« Mes accès ») |
| **Développement** | `/api/dev` | **nouveau** — membres dev, outils internes |
| Sécurité | `/api/security` | événements (paginés `{items,total}`), comptes verrouillés, sessions actives, stats |
| Chat, notifications | `/api/chat`, `/api/notifications`, `/ws` | temps réel |
| Public | `/api/public` | catalogue + envoi de demande, sans authentification |
| Cron | `/api/cron/check-deadlines` | protégé par l'en-tête `X-Cron-Secret` |

## 5. Caisse

- **Journal append-only** : aucune route de modification ni de suppression.
- Une erreur se corrige par une **écriture inverse** (`POST /transactions/{id}/reverse`) avec motif obligatoire ; un mouvement ne s'annule qu'une fois et une annulation n'est pas annulable.
- La **date est imposée par le serveur** (pas d'antidatage). Références `CAI-AAAA-00001`.
- **Clôture journalière** (`POST /closings`) : calcule solde d'ouverture, entrées, sorties, solde de clôture, écart avec le comptage ; passe les mouvements à `CLOTUREE`. Après clôture du jour, plus d'écriture ni d'annulation avant le lendemain.
- **Audit** : chaque action est écrite dans `audit_logs` (`cash.transaction.created`, `.reversed`, `cash.closed`), lisible via `GET /audit` (`cash.audit`).
- **Export CSV** neutralisé contre l'injection de formules.
- **Un seul compte actif** peut écrire dans la caisse (`MAX_CASH_OPERATORS=1`). Contrôle à la création d'un membre, au changement de rôle, à la réactivation et à la modification des permissions d'un rôle.
- **Rapprochement caisse → finance** : une entrée de caisse rattachée à une prestation (`project_service_id`) crée automatiquement le paiement correspondant (mode `CASH`, revenu créé au besoin au montant convenu), dans la même transaction base de données. Refus si la devise diffère de celle de la prestation (400) ou si le montant dépasse le reste à payer (409).
- L'**annulation** d'un encaissement annule aussi le paiement lié : il reçoit `voided_at`, reste visible dans le détail mais est exclu des soldes. Une sortie rattachée à une prestation n'est qu'une étiquette (aucune rémunération créée). Les deux actions sont tracées dans l'audit (`finance.payment.created_from_cash`, `finance.payment.voided_from_cash`).
- Le CEO **voit tout** (solde, mouvements, clôtures, audit, export) mais **n'écrit pas**.
- Le CEO peut désactiver le caissier puis en créer un autre : accepté, tracé dans l'audit.

## 6. Équipe de développement

- `DevMembership.level = MEMBER` : appartient à l'équipe dev, accès limité.
- `DevMembership.level = INTERNAL` : en plus, accès aux outils internes (`GET /api/dev/tools`) — exige la permission `dev.tools.use` **et** le niveau `INTERNAL`.
- Attribution et retrait par le CEO (`dev.manage`), tracés dans l'audit. La liste des outils internes est pour l'instant un catalogue statique dans `routers/dev.py`.

## 7. Base de données

Chaîne Alembic linéaire : `c258e0ab76cc` → `ad647d7d91fc` → `a021f4275673` → `6862a8d269f3` → `872272390752` → `580727017d23` → `185e4d362a81` → `2eaf395a08e5` → `a1aef567664a` → `b7c1d2e3f405` → **`c9d8e7f6a5b4`**.

`b7c1d2e3f405` ajoute `users.employment_status` et les tables `cash_closings`, `cash_transactions`, `dev_memberships`. `c9d8e7f6a5b4` ajoute `payments.cash_transaction_id` (unique) et `payments.voided_at`. Aucune des deux n'a été exécutée sur PostgreSQL ; seule la correspondance colonnes ↔ modèles a été vérifiée.

Deux migrations sont des doublons vides (`872272390752`, `2eaf395a08e5`). Elles sont inoffensives mais ne doivent plus être supprimées maintenant qu'elles sont chaînées.

## 8. Corrections apportées à cette session

- `POST /api/public/requests` ne retournait rien (erreur 500) : corrigé, notifie CEO + DA en plus.
- Montage `/storage` : le dossier est créé s'il manque.
- **Finance** : les écritures passent de `require_roles("CEO")` à `finance.manage`, exclu du joker `*` ; lectures sur `finance.view`. Rôle `COMPTABLE` seedé. **Conséquence** : tant qu'aucun compte comptable n'existe, personne ne peut saisir revenus, paiements ou rémunérations, et les boutons de création de `finances.js` répondent 403 pour le CEO.
- Tests : la fixture CEO reçoit le joker `*` comme en production ; le test sécurité lit la réponse paginée.

## 9. Points critiques et d'attention

### Corrigés (lot sécurité, migration `d1e2f3a4b5c6`)

1. **Contrôles par nom de rôle supprimés** : plus aucun `require_roles` dans les routeurs. Clients, demandes, projets, activités, documents, publications, portfolio, services et sécurité passent par `require_permission` / `require_any_permission`. Les filtres internes du type « un CM ne voit que ses éléments » testent aussi des permissions (`user_can`). Nouvelles permissions : `security.view`, `security.manage`, `chat.manage`.
2. **Mot de passe** : 10 caractères minimum, une lettre et un chiffre, 128 maximum, côté API (création, réinitialisation, changement).
3. **Jetons révocables** : `users.token_version` est copié dans le JWT (`tv`) et revérifié à chaque requête et à chaque connexion WebSocket. Changer ou réinitialiser un mot de passe coupe toutes les sessions.
4. **WebSocket** : refuse (code 4401) un compte désactivé ou un jeton révoqué.
5. **Mot de passe oublié** : `POST /api/auth/forgot-password` (réponse identique que le compte existe ou non, 5 demandes par IP et par 15 min) notifie les détenteurs de `team.manage`. Le CEO génère un lien avec `POST /api/users/{id}/reset-link` (usage unique, 30 min, empreinte SHA-256 stockée). L'intéressé choisit son mot de passe via `/app/reset-password.html` (`POST /api/auth/reset-password`). Changement connecté : `POST /api/auth/change-password`. CEO verrouillé hors de l'application : `python -m app.reset_password --email …`.
6. **Comptes sensibles (caisse, finance)** : à la création, ou au passage vers un tel rôle, le mot de passe fourni est ignoré et le compte attend un lien (en-tête `X-Password-Setup: reset-link-required`). `POST /users/{id}/reset-password` (le CEO impose un mot de passe) répond 409 pour ces comptes.
7. **Limite par IP** : 20 échecs de connexion par IP et par 15 min (429), calculés sur `security_events`. Cela empêche de reverrouiller le CEO en boucle depuis une même adresse.
8. **Fichiers** : documents limités à une liste d'extensions, signature binaire vérifiée, nom disque généré par le serveur, type MIME déduit de l'extension (jamais du client), nom d'affichage assaini, projet vérifié, `nosniff` au téléchargement. Portfolio : SVG refusé, extension dérivée du type, signature vérifiée. Les deux fichiers étaient auparavant acceptés tels quels.
9. **Stockage** : seul `/storage/portfolio` est servi publiquement. `storage/documents` ne l'est plus ; l'accès passe par `/api/documents/{id}/download` (authentifié + permission).
10. **Secrets** : `ENVIRONMENT=production` refuse de démarrer si `SECRET_KEY` est par défaut ou fait moins de 32 caractères, ou si `CRON_SECRET` (24+ caractères, différent de `SECRET_KEY`) manque. Le cron compare l'en-tête à temps constant ; hors production, il retombe sur `SECRET_KEY` si `CRON_SECRET` est absent.
11. **Notifications** : `notify_staff` cible la permission `requests.manage`, plus des rôles nommés.

### Restent ouverts

1. **Le CEO voit le lien qu'il génère** et pourrait l'utiliser lui-même pour prendre la main sur un compte caisse. C'est désormais détectable (audit, `security_events`, notification à l'intéressé à la génération puis à la modification, sessions révoquées), mais pas impossible. La vraie prévention demande un envoi du lien directement à l'utilisateur (e-mail) ou une double authentification que l'intéressé enrôle lui-même.
2. **Jeton WebSocket dans l'URL** (`/ws?token=`) : un navigateur ne peut pas envoyer d'en-tête sur un WebSocket. À remplacer par un ticket à usage unique et courte durée.
3. **JWT de 24 h sans refresh** : la révocation corrige le risque, pas l'ergonomie.
4. **Limite par IP derrière un proxy** : lancer `uvicorn --proxy-headers --forwarded-allow-ips=<ip du proxy>`, sinon tous les visiteurs partagent le même compteur.
5. **Rapprochement de caisse** : la permission `cash.reconcile` existe mais aucune route dédiée (le comptage se saisit à la clôture).
6. **Pas de CORS configuré** : correct tant que l'API et le frontend restent sur la même origine.
7. `.env` : ne pas le versionner.

### À faire au déploiement

- `alembic upgrade head` (tête `d1e2f3a4b5c6`), puis `python -m app.seeds` (nouvelles permissions et `chat.manage` pour le DA).
- Définir `ENVIRONMENT=production`, une `SECRET_KEY` de 32+ caractères et un `CRON_SECRET` distinct ; mettre à jour le cron avec ce secret.
- Vérifier que le frontend n'appelle plus `/storage/documents/...` directement.
- Le formulaire de création de membre doit afficher les erreurs 422 de la règle de mot de passe, et appeler `reset-link` après la création d'un compte caisse ou finance.
- Tests : 34 tests verts sur SQLite ; migrations non exécutées sur PostgreSQL.

## 10. Frontend

**Identité** : vert `#015a4c`, rouge `#bb3c39`, noir `#212521`, avec un dégradé de marque vert → rouge (`--grad-brand`) sur les boutons principaux, les icônes et les liserés, et un fond vert → noir → rouge. Appliquée à l'application, à la partie publique, aux pages de connexion et de réinitialisation, aux icônes et au manifeste. Un vert plus clair (`--accent-text`, contraste 7:1) sert au texte sur fond sombre, car `#015a4c` seul y est illisible (1,9:1). Le cache du service worker passe en `kimia-app-v2` pour forcer le nouveau thème.

**Pages ajoutées** (`frontend/app/assets/js/pages/`)

| Page | Contenu |
|---|---|
| `cash.js` | Solde, mouvements, clôtures, audit. Saisie, annulation, clôture et rattachement à une prestation pour le caissier ; supervision en lecture seule pour le CEO ; export CSV |
| `access.js` | « Mes accès » pour tous ; « Rôles & permissions » (création de rôles, cases à cocher par module) avec `roles.manage` |
| `dev.js` | Équipe dev : membre / dev interne, ajout, modification, retrait, outils internes pour les devs internes |

**Pages modifiées** : `finances.js` (boutons d'écriture masqués sans `finance.manage`), `team.js` (lien de réinitialisation à la place du mot de passe imposé, lien proposé à la création d'un membre), `login.html` (« Mot de passe oublié ? »), `reset-password.html` (nouveau design, jeton retiré de l'URL après lecture), `shell.js` (menu Caisse, Développement, Mes accès).

Les boutons d'écriture se déterminent avec `GET /api/access/me` (`modules.*`) et non avec la présence de `*` dans les permissions, puisque le joker du CEO ne couvre pas la caisse ni `finance.manage`. Nouvel endpoint backend pour la saisie : `GET /api/cash/receivables` (prestations avec reste à payer, réservé à `cash.create`).

**Vérifié** : serveur réel sur PostgreSQL, chaque page rendue avec un CEO puis un caissier (aucune valeur `undefined`/`NaN`, bons boutons selon le rôle), migrations appliquées et seeds deux fois sans doublon, `alembic check` sans écart, 35 tests verts. **Non vérifié** : affichage dans un vrai navigateur (couleurs, mise en page mobile) et clics sur les formulaires.

**Reste à faire** : profil personnel (photo, bio, disponibilité), palette de commandes (Ctrl+K), centre de contrôle du CEO, page Organisation, navigation personnalisable, alertes automatiques, route de rapprochement de caisse.

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
│  │     ├─ b7c1d2e3f405_add_cash_dev_employment_status.py
│  │     ├─ c258e0ab76cc_initial_schema.py
│  │     ├─ c9d8e7f6a5b4_link_payments_to_cash.py
│  │     └─ d1e2f3a4b5c6_token_version_and_password_reset.py
│  ├─ alembic.ini
│  ├─ app
│  │  ├─ config.py
│  │  ├─ core
│  │  │  ├─ access.py
│  │  │  ├─ audit.py
│  │  │  ├─ cash_guard.py
│  │  │  ├─ deps.py
│  │  │  ├─ notifications.py
│  │  │  ├─ ratelimit.py
│  │  │  ├─ security.py
│  │  │  ├─ uploads.py
│  │  │  ├─ ws_manager.py
│  │  │  └─ __init__.py
│  │  ├─ create_user.py
│  │  ├─ database.py
│  │  ├─ main.py
│  │  ├─ models
│  │  │  ├─ auth.py
│  │  │  ├─ business.py
│  │  │  ├─ cash.py
│  │  │  ├─ chat.py
│  │  │  ├─ content.py
│  │  │  ├─ dev.py
│  │  │  ├─ finance.py
│  │  │  ├─ workflow.py
│  │  │  └─ __init__.py
│  │  ├─ reset_password.py
│  │  ├─ routers
│  │  │  ├─ access.py
│  │  │  ├─ activities.py
│  │  │  ├─ auth.py
│  │  │  ├─ cash.py
│  │  │  ├─ chat.py
│  │  │  ├─ clients.py
│  │  │  ├─ cron.py
│  │  │  ├─ dev.py
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
│  │  │  ├─ access.py
│  │  │  ├─ auth.py
│  │  │  ├─ business.py
│  │  │  ├─ cash.py
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
│     ├─ test_cash_access.py
│     ├─ test_security_hardening.py
│     └─ __init__.py
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
│  │  │        ├─ access.js
│  │  │        ├─ activities.js
│  │  │        ├─ cash.js
│  │  │        ├─ chat.js
│  │  │        ├─ clients.js
│  │  │        ├─ dashboard.js
│  │  │        ├─ dev.js
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
│  │  ├─ reset-password.html
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