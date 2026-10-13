"""
Entry point
===========
1. Initialises the database
2. Seeds 20 sample complaints + 6 demo users (first run only)
3. Runs the full analysis pipeline on unprocessed complaints
4. Starts the Flask development server

Usage:
    python main.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

from src.db.models import init_db, SessionLocal
from src.db.seed import seed
from src.utils.pipeline import run_pipeline
from src.api import create_app


def main():
    print("=" * 55)
    print("  Customer Complaint Intelligence System")
    print("=" * 55)

    # Step 1 — Database setup
    print("\n[1/4] Initialising database...")
    init_db()

    # Step 2 — Seed sample data (complaints + users)
    print("[2/4] Seeding sample complaints...")
    seed()

    # Step 3 — Run analysis pipeline
    print("[3/4] Running analysis pipeline...")
    db = SessionLocal()
    try:
        result = run_pipeline(db)
        print(f"      ✓ {result['message']}")
    finally:
        db.close()

    # Step 4 — Start API
    print("[4/4] Starting Flask API...\n")
    print("  API running at:  http://127.0.0.1:5000")
    print("  Dashboard:       GET  /")
    print("  Customer portal: GET  /customer")
    print("  Mgmt portal:     GET  /management")
    print("  List complaints: GET  /api/complaints")
    print("  Priority view:   GET  /api/complaints/priority")
    print("  Clusters:        GET  /api/complaints/clusters")
    print("  Summary stats:   GET  /api/complaints/summary")
    print("  Submit new:      POST /api/complaints")
    print()
    print("  ── Demo Credentials ─────────────────────────────────")
    print()
    print("  CUSTOMER PORTAL  →  http://127.0.0.1:5000/customer")
    print("  ┌─────────────┬──────────────┬─────────────────────┐")
    print("  │ Username    │ Password     │ Name                │")
    print("  ├─────────────┼──────────────┼─────────────────────┤")
    print("  │ alice       │ alice123     │ Alice Johnson       │")
    print("  │ bob         │ bob123       │ Bob Smith           │")
    print("  │ carol       │ carol123     │ Carol White         │")
    print("  │ demo        │ demo123      │ Demo Customer       │")
    print("  └─────────────┴──────────────┴─────────────────────┘")
    print()
    print("  MANAGEMENT PORTAL  →  http://127.0.0.1:5000/management")
    print("  ┌─────────────┬──────────────┬─────────────────────┐")
    print("  │ Username    │ Password     │ Name                │")
    print("  ├─────────────┼──────────────┼─────────────────────┤")
    print("  │ admin       │ admin123     │ Admin User          │")
    print("  │ manager1    │ manager123   │ Sarah Manager       │")
    print("  └─────────────┴──────────────┴─────────────────────┘")
    print()
    print("  Press Ctrl+C to stop.\n")

    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG", "0") == "1")


if __name__ == "__main__":
    main()
