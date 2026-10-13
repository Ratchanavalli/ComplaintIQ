# Customer Complaint Intelligence System

Automatically analyses customer complaints using four AI stages:

| Stage | What it does |
|---|---|
| **Categorization** | Labels each complaint: delivery / refund / product_quality / customer_service / other |
| **Sentiment Analysis** | Scores tone: positive / neutral / negative (-1 to +1) |
| **Grouping** | Clusters similar complaints to surface systemic problems |
| **Priority Scoring** | Ranks complaints 0–100 (critical / high / medium / low) |

---

## Quick Start

### 1. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows PowerShell
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Download NLTK data (one-time)
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger')"
```

### 4. Run the system
```bash
python main.py
```

This will:
- Create the SQLite database in `data/complaints.db`
- Seed 20 sample complaints
- Run the full analysis pipeline
- Start the Flask API at `http://127.0.0.1:5000`

---

## API Endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/api/complaints` | Submit a new complaint |
| GET | `/api/complaints` | List all complaints |
| GET | `/api/complaints/<id>` | Get one complaint |
| GET | `/api/complaints/summary` | Stats overview |
| GET | `/api/complaints/clusters` | Grouped problem clusters |
| GET | `/api/complaints/priority` | Sorted by priority score |
| POST | `/api/complaints/run-pipeline` | Reprocess unanalysed complaints |

### Submit a complaint (example)
```bash
curl -X POST http://127.0.0.1:5000/api/complaints \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "C099",
    "customer_name": "Test User",
    "complaint_text": "My package never arrived and customer service keeps hanging up on me!",
    "channel": "web"
  }'
```

### Filter complaints
```
GET /api/complaints?category=delivery&sentiment=negative&sort=priority_score&order=desc
```

---

## Run Tests
```bash
pytest
```

---

## Project Structure
```
complaint-intelligence/
├── main.py                     ← entry point
├── requirements.txt
├── .env
├── data/
│   └── complaints.db           ← SQLite database (auto-created)
├── src/
│   ├── categorization/         ← Stage 1: category detection
│   ├── sentiment/              ← Stage 2: sentiment scoring
│   ├── grouping/               ← Stage 3: K-Means clustering
│   ├── priority/               ← Stage 4: priority scoring
│   ├── api/                    ← Flask REST API
│   ├── db/                     ← SQLAlchemy models + seed data
│   └── utils/                  ← analysis pipeline orchestrator
└── tests/                      ← pytest unit tests
```
