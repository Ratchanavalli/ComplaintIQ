# Customer Complaint Intelligence — Final Summary

## What Was Enhanced

- **Authentication & role-based access**: New `User` model, `auth.py` helpers (password hashing, session decorators), and `/auth/login`, `/auth/logout`, `/auth/me` endpoints. Six demo accounts seeded automatically (4 customers, 2 managers).
- **Backend API extended**: 10+ new routes added to `routes.py` — complaint detail, respond, internal note, status PATCH, similar complaints, priority explanation, early-warning alerts, and trend data — all guarded by `@login_required` / `@manager_required`.
- **Customer portal** (`/customer`): Dark blue/teal ShopIQ-branded single-page app. Login, "My Complaints" tab (owner-filtered), "Submit Complaint" tab (AI analysis card on submission), and "Track Complaint" tab (status timeline + management responses).
- **Management portal** (`/management`): Purple/indigo single-page app with 5-section sidebar — Dashboard (stats + early-warning banner), Complaints (table + filters), Manage Complaint (full AI detail, respond, note, status update), Analytics (trend charts), and Alerts (volume spikes, high-risk clusters, critical recent).
- **Database schema extended**: Added `users`, `complaint_responses`, and `internal_notes` tables; added `status`, `assigned_to`, `resolution_notes`, and `resolved_at` columns to `complaints`. All migrations are additive via `Base.metadata.create_all()`.

## Features Already Working and Preserved

- Original dashboard at `/` — public, no login required, shows all stats/clusters/priority breakdown.
- Full AI pipeline: automatic categorization, sentiment analysis, priority scoring with breakdown, cluster grouping.
- Flask API with all original endpoints (`/api/complaints`, `/api/complaints/summary`, `/api/complaints/clusters`, `/api/complaints/priority`, `/api/complaints/run-pipeline`).
- SQLite persistence via `data/complaints.db` — 20 seeded complaints and 6 demo users already present.
- `python main.py` one-command startup with DB init, seeding, pipeline, and server launch.

## Run the Application

```
cd complaint-intelligence && python main.py
```

Then open your browser. The server binds to `http://127.0.0.1:5000`.

## Customer Demo Flow

1. Open **http://127.0.0.1:5000/customer**
2. Log in as `alice` / `alice123`
3. "My Complaints" tab — see Alice's existing complaints only
4. "Submit Complaint" tab — fill in the form, submit, see the AI analysis card (category, sentiment, priority score)
5. "Track Complaint" tab — pick a complaint to view the full status timeline and any management responses

## Management Demo Flow

1. Open **http://127.0.0.1:5000/management**
2. Log in as `admin` / `admin123` (or `manager1` / `manager123`)
3. **Dashboard** — stat cards (Total, Critical, Negative, Avg Score), charts, early-warning banner
4. **Complaints** — full table with category/sentiment/priority/status filters; click "Manage" on any row
5. **Manage Complaint** — AI analysis, priority explanation, similar complaints, respond to customer, add internal note, update status
6. **Analytics** — trend charts (last 14 days by day, last 7 days by category)
7. **Alerts** — volume spikes, high-risk clusters, critical recent complaints

Demo credentials hint box is shown on both login screens.

## Known Limitations

- **No real SSO**: The customer portal simulates a company-integrated login for demo purposes. A real deployment would replace the login form with an OAuth/OIDC flow.
- **Server-side status filter**: The complaints list endpoint does not filter by status server-side; the management portal applies the status filter client-side.
- **AI pipeline**: Uses rule-based keyword matching for categorization and sentiment (no external ML model). Results are honest and clearly presented as AI-assisted estimates.
- **Development server**: Flask's built-in server is used. For production, a WSGI server (Gunicorn, Waitress) should replace it.
- **No automated tests** for the new auth/portal routes — manual verification against acceptance criteria was performed.
