# Implementation Plan — Customer Complaint Intelligence Enhancement

## Codebase findings (read before planning)

- **Entry point**: `main.py` — init DB → seed → pipeline → Flask server
- **Existing DB tables**: `complaints`, `clusters`, `processing_logs` — all preserved
- **Existing routes**: all public (no auth), served by `api_bp` Blueprint in `src/api/routes.py`
- **Static files**: `static/index.html` — working dashboard at `/`; `static/customer.html` and `static/management.html` **do not exist yet**
- **Auth**: no auth exists yet — `src/api/auth.py` and `src/api/auth_routes.py` are new files
- **werkzeug** already installed (Flask dependency); `generate_password_hash`/`check_password_hash` available
- **Flask session** (signed cookie) will be used — no `flask-session` package needed
- **SECRET_KEY** already set in `.env` as `complaint-intelligence-secret-key`
- **Priority breakdown** available from `src/priority/scorer.calculate_priority()` returning `{priority_score, priority_level, breakdown: {sentiment_pts, category_pts, urgency_pts, cluster_pts}}`
- **No pandas** — all trend/alert queries must use pure SQLAlchemy
- **index.html** at `/` must remain working without auth — existing read-only GET routes stay public; only new routes + POST /api/complaints get auth guards

---

## FEAT decomposition

This work decomposes cleanly into 3 sequential features:

| FEAT | What | Depends on |
|------|------|-----------|
| FEAT-001 | Full backend: models + auth + new routes + seed + main.py | nothing |
| FEAT-002 | Customer portal HTML (`static/customer.html`) | FEAT-001 |
| FEAT-003 | Management portal HTML (`static/management.html`) | FEAT-001 |

FEAT-002 and FEAT-003 are independent of each other but both depend on FEAT-001.
Full FEAT artifacts are at `.agents/tasks/features/FEAT-001.json`, `FEAT-002.json`, `FEAT-003.json`.

---

## Steps (ordered by dependency)

- [ ] 1. **Extend `src/db/models.py`** — add three new tables and four new columns on Complaint.
      Add `User` table (id, username, password_hash, role, full_name, email).
      Add `ComplaintResponse` table (id, complaint_id FK, manager_id FK, response_text, created_at, is_visible_to_customer).
      Add `InternalNote` table (id, complaint_id FK, manager_id FK, note_text, created_at).
      Add nullable columns to `Complaint`: status (String 30, default 'open'), assigned_to (Integer FK users.id), resolution_notes (Text), resolved_at (DateTime).
      Add relationships: `Complaint.responses`, `Complaint.notes`, `Complaint.assignee`.
      `init_db()` already calls `Base.metadata.create_all` — no change needed; SQLite additive migration is safe.
      **Files**: `src/db/models.py`
      **Verify**: `python -c "from src.db.models import User, ComplaintResponse, InternalNote; print('OK')"` exits 0.

- [ ] 2. **Create `src/api/auth.py`** — session-cookie auth helpers (no JWT).
      Import `generate_password_hash`, `check_password_hash` from `werkzeug.security`.
      Implement: `hash_password(plain)`, `check_password(plain, hashed)`, `login_required` decorator (401 if no session user_id), `manager_required` decorator (403 if role != manager), `current_user_id()`, `current_role()`.
      **Files**: `src/api/auth.py` (CREATE NEW)
      **Verify**: `python -c "from src.api.auth import login_required, manager_required, hash_password; print('OK')"` exits 0.

- [ ] 3. **Create `src/api/auth_routes.py`** — Blueprint `auth_bp` at `/auth`.
      `POST /auth/login`: query User by username, check_password, set session, return role/username/full_name or 401.
      `POST /auth/logout`: clear session.
      `GET /auth/me`: return current user info or 401.
      **Files**: `src/api/auth_routes.py` (CREATE NEW)
      **Depends on**: Step 1 (User model), Step 2 (auth helpers)
      **Verify**: `python -c "from src.api.auth_routes import auth_bp; print('OK')"` exits 0.

- [ ] 4. **Extend `src/api/routes.py`** — auth guards on new routes only; new endpoints.
      Import `login_required`, `manager_required`, `current_user_id`, `current_role` from `src.api.auth`.
      Import `User`, `ComplaintResponse`, `InternalNote` from `src.db.models`.
      **Auth guards**: Add `@login_required` to `submit_complaint` (POST) only. Keep all existing GET routes public (so `index.html` at `/` keeps working without auth).
      **Customer ownership filter**: In `list_complaints`, if `current_role() == 'customer'`, add `.filter(Complaint.customer_id == str(current_user_id()))`.
      **New routes** (all new, no existing routes modified destructively):
      - `GET /api/complaints/<id>/detail` — `@login_required`, ownership check for customers, returns full complaint + responses
      - `POST /api/complaints/<id>/respond` — `@manager_required`, creates `ComplaintResponse`, sets status to `in_progress` if `open`
      - `POST /api/complaints/<id>/note` — `@manager_required`, creates `InternalNote`
      - `PATCH /api/complaints/<id>/status` — `@manager_required`, updates status, sets `resolved_at` if `resolved`
      - `GET /api/complaints/<id>/responses` — `@login_required`, ownership check, returns visible responses
      - `GET /api/complaints/alerts` — `@manager_required`, early-warning: volume spikes (this week vs last week per category), high-risk clusters (avg_priority_score > 75), critical complaints in last 48h — pure SQLAlchemy, no pandas
      - `GET /api/complaints/<int:complaint_id>/similar` — `@manager_required`, top 5 same cluster by priority_score DESC
      - `GET /api/complaints/<int:complaint_id>/priority-explanation` — `@login_required`, re-runs `calculate_priority()` with breakdown, returns human-readable text + raw breakdown
      - `GET /api/complaints/trends` — `@manager_required`, counts by day last 14 days + by category last 7 days, pure SQLAlchemy
      Add `status` field to `_complaint_dict()` serializer.
      **Files**: `src/api/routes.py`
      **Depends on**: Steps 1, 2, 3
      **Verify**: `python -c "from src.api import create_app; app=create_app(); rules=[r.rule for r in app.url_map.iter_rules()]; assert any('/alerts' in r for r in rules); print('OK')"` exits 0.

- [ ] 5. **Extend `src/db/seed.py`** — add `seed_users()`.
      Import `hash_password` from `src.api.auth` and `User` from `src.db.models`.
      `DEMO_USERS` list: admin/admin123/manager, manager1/manager123/manager, alice/alice123/customer, bob/bob123/customer, carol/carol123/customer, demo/demo123/customer.
      `seed_users()`: skip if `db.query(User).count() > 0`; create all 6 users with hashed passwords; link existing complaints to alice/bob/carol by matching `complaint.email` to user email, setting `complaint.customer_id = str(user.id)`.
      Call `seed_users()` from the bottom of `seed()`.
      **Files**: `src/db/seed.py`
      **Depends on**: Steps 1, 2
      **Verify**: delete `data/complaints.db`, run `python main.py`, check startup output shows users seeded; confirm DB has 6 users with `python -c "from src.db.models import SessionLocal, User; db=SessionLocal(); print(db.query(User).count())"`.

- [ ] 6. **Update `src/api/__init__.py`** — register auth_bp, add SECRET_KEY, add portal routes.
      Add `import os` if not present.
      In `create_app()`: set `app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')` and `app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'`.
      `app.register_blueprint(auth_bp)` from `src.api.auth_routes`.
      Add `@app.route('/customer')` serving `static/customer.html`.
      Add `@app.route('/management')` serving `static/management.html`.
      Keep existing `@app.route('/')` and `@app.route('/health')` unchanged.
      **Files**: `src/api/__init__.py`
      **Depends on**: Step 3
      **Verify**: `python -c "from src.api import create_app; app=create_app(); rules=[r.rule for r in app.url_map.iter_rules()]; assert '/customer' in rules and '/management' in rules; print('OK')"` exits 0.

- [ ] 7. **Update `main.py`** — add demo credentials to startup output.
      After the `[4/4] Starting Flask API...` block, add a formatted demo credentials section:
      ```
        Demo Portals:
          Customer Portal:   http://127.0.0.1:5000/customer
          Management Portal: http://127.0.0.1:5000/management
          Original Dashboard: http://127.0.0.1:5000/

        Demo Customer Accounts:       Demo Management Accounts:
          alice  / alice123             admin    / admin123
          bob    / bob123               manager1 / manager123
          carol  / carol123
          demo   / demo123
      ```
      **Files**: `main.py`
      **Depends on**: Step 6
      **Verify**: `python main.py` starts and prints the demo credential block.

- [ ] 8. **Create `static/customer.html`** — ShopIQ customer portal, dark blue/teal theme.
      Self-contained single HTML file, inline CSS and JS, no build step, no npm.
      CSS theme: `--bg:#060d14`, `--surface:#0a1628`, `--accent:#0ea5e9`, `--accent2:#06b6d4`, `--text:#e2e8f0`, `--muted:#64748b` — visually distinct from the purple/indigo management theme.
      **Login screen** (shown before auth): ShopIQ branding, username/password form, demo account hint card (alice/alice123, bob/bob123, carol/carol123, demo/demo123). On load: `GET /auth/me` — skip login if already logged in as customer.
      **After login — 3 tabs**:
      - *My Complaints*: calls `GET /api/complaints`; backend filters by customer_id automatically (FEAT-001 Step 4). Table: ID, Category badge, Sentiment, Priority, Status badge, Date, View button. Status filter dropdown. Empty-state card.
      - *Submit Complaint*: form with order_id, product_id, channel dropdown, complaint_text textarea. `POST /api/complaints` — customer_id set by backend from session. On success show AI analysis result card (category, sentiment, priority score + bar). Toast notification.
      - *Track Complaint*: search by complaint ID or click View from My Complaints. `GET /api/complaints/<id>/detail` for text/metadata. `GET /api/complaints/<id>/priority-explanation` for AI explanation. Visual status timeline (4 steps: Open → In Progress → Resolved → Closed). Management responses list (no internal notes). Security disclaimer at bottom.
      **Security**: reject login if role != customer ("This portal is for customers only").
      **Files**: `static/customer.html` (CREATE NEW)
      **Depends on**: Steps 1–6 (all backend must be in place)
      **Verify**: `GET http://127.0.0.1:5000/customer` returns 200; login as alice/alice123 — My Complaints shows Alice's complaints; submit complaint appears; track view loads AI explanation.

- [ ] 9. **Create `static/management.html`** — ShopIQ Intelligence Platform management portal, purple/indigo theme.
      Self-contained single HTML file, inline CSS and JS.
      CSS theme: same as `index.html` (purple/indigo: `--indigo:#6366f1`, `--violet:#8b5cf6`) with management-specific additions.
      **Login screen**: admin/admin123, manager1/manager123 hint. Reject role != manager. `GET /auth/me` on load.
      **Sidebar with 5 sections**:
      1. *Dashboard* — `GET /api/complaints/summary` stat cards (Total, Critical, Negative, Avg Score). Category bar chart, sentiment donut (SVG, same pattern as index.html). `GET /api/complaints/alerts` early-warning banner (red/orange if alerts exist, green 'all normal' if not).
      2. *Complaints* — `GET /api/complaints` with filter params (category, sentiment, priority). Add status dropdown filter. Table identical to All Complaints in index.html + Status badge + Manage button.
      3. *Manage Complaint* — loaded when Manage clicked. Two-column: complaint text/metadata left, AI analysis right. AI card: category, sentiment, priority score bar + `GET /api/complaints/<id>/priority-explanation` rendered as readable text. Similar complaints: `GET /api/complaints/<id>/similar` — top 5 list with priority badges. Actions: (a) status dropdown + Update → `PATCH /api/complaints/<id>/status`; (b) response textarea + Send → `POST /api/complaints/<id>/respond` (labelled "Customer will see this"); (c) note textarea + Add → `POST /api/complaints/<id>/note` (labelled "Internal only"). Existing responses list below (show both visible + notes with Private label for notes).
      4. *Analytics* — category/sentiment/priority charts from summary. Trend section: `GET /api/complaints/trends` — complaints per day (14 days) as horizontal bar chart; by category (7 days). Pure SVG, no chart libraries.
      5. *Alerts* — `GET /api/complaints/alerts`. Three subsections: Volume Spikes table, High-Risk Clusters cards, Critical Recent complaints table. Refresh button + last-refreshed timestamp.
      **Files**: `static/management.html` (CREATE NEW)
      **Depends on**: Steps 1–6 (all backend must be in place)
      **Verify**: `GET http://127.0.0.1:5000/management` returns 200; login as admin/admin123 — dashboard loads with charts; all 5 sections navigate without JS errors; respond action creates visible response in customer portal; `GET http://127.0.0.1:5000` still loads without auth.

---

## Conflict notes and decisions

1. **Auth scope**: Existing GET routes (`/api/complaints`, `/api/complaints/summary`, etc.) stay **public** — this keeps `index.html` at `/` working without auth. Only `POST /api/complaints` and all new routes get auth guards.

2. **customer_id after auth**: The `submit_complaint` route will use `str(current_user_id())` as customer_id when called from the customer portal. The existing seed data has string customer_ids like "C001" — these remain; new portal submissions will have numeric string IDs matching the User.id. The ownership check `complaint.customer_id == str(session['user_id'])` handles both cases.

3. **SQLite additive migration**: No Alembic migration needed. `Base.metadata.create_all(bind=engine)` in `init_db()` creates new tables on restart. New nullable columns on `Complaint` are safe for existing rows (all default to NULL / 'open').

4. **No pandas**: All trend and alert queries use SQLAlchemy `func.count()`, `func.date()` (SQLite `strftime`), and Python date arithmetic.

5. **Route ordering conflict**: `GET /api/complaints/alerts` must be registered **before** `GET /api/complaints/<int:complaint_id>` in the Blueprint to avoid Flask matching "alerts" as an integer id. Use `@api_bp.route("/complaints/alerts")` before `@api_bp.route("/complaints/<int:complaint_id>/...")`.

6. **Session cookie**: Flask's built-in signed session (cookie) is used. `SECRET_KEY` already in `.env`. No `flask-session` package needed.

7. **werkzeug**: Already installed as a Flask transitive dependency; `from werkzeug.security import generate_password_hash, check_password_hash` works without adding to `requirements.txt`.
