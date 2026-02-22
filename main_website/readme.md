# IntelliPrep Main Website — Setup & Run Guide

## Environment Variables Required

Copy `.env.example` to `.env` and fill in your values:

```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key     ← KEEP THIS SECRET
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
APP_SECRET_KEY=any-random-long-string
```

### Where to find each:
| Variable | Location in Supabase Dashboard |
|---|---|
| `SUPABASE_URL` | Project Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Project Settings → API → anon public |
| `SUPABASE_SERVICE_KEY` | Project Settings → API → service_role (secret) |
| `DATABASE_URL` | Project Settings → Database → Connection string → URI |

---

## Running Locally

```bash
# Create and activate venv (already done)
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies (already done)
pip install -r requirements.txt

# Start the dev server
uvicorn app.main:app --reload --port 8000
```

Then open http://localhost:8000

---

## Project Structure

```
main_website/
├── app/
│   ├── main.py               ← FastAPI entry point
│   ├── config.py             ← Environment config & constants
│   ├── db.py                 ← Postgres connection pool
│   ├── supabase_client.py    ← Supabase anon + admin clients
│   ├── dependencies.py       ← Auth dependency (get_current_user)
│   ├── routers/
│   │   ├── auth.py           ← /auth/login, /register, /logout
│   │   ├── dashboard.py      ← /dashboard
│   │   ├── test.py           ← /test/* (full test lifecycle)
│   │   └── analytics.py      ← /analytics/
│   ├── services/
│   │   └── skill_profile.py  ← Compute & persist user skill profile
│   ├── test_engine/
│   │   ├── calibration.py    ← Calibration test generator
│   │   ├── adaptive.py       ← Adaptive test generator
│   │   └── ml_interface.py   ← ⬅ ML MODEL INTEGRATION POINT
│   ├── static/
│   │   ├── css/main.css
│   │   └── js/main.js
│   └── templates/
│       ├── base.html
│       ├── auth_base.html
│       ├── auth/login.html
│       ├── auth/register.html
│       ├── dashboard.html
│       ├── analytics.html
│       ├── test/
│       │   ├── question_list.html
│       │   ├── question.html
│       │   └── result.html
│       └── errors/404.html
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## ML Model Integration

Open `app/test_engine/ml_interface.py`.

Replace the body of `predict_success_probabilities()` with your model call:

```python
def predict_success_probabilities(user_id, question_ids, skill_profile):
    # Your model here — return dict[question_id → float in [0,1]]
    ...
```

The adaptive generator in `adaptive.py` will automatically use your probabilities
to select questions in the 0.45–0.75 target probability window.

---

## Database Schema (DO NOT MODIFY)

Tables used: `main_questions`, `main_tests`, `main_attempts`, `main_user_skill`, `main_users`  
Auth: Supabase `auth.users`

See `main_website_old/database.md` for the full schema documentation.
