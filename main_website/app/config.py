import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-me-in-production")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")

if not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_SERVICE_KEY must be set in .env (needed for write operations)")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in .env")

# ─── Test / Domain Constants ──────────────────────────────────────────────────
CALIBRATION_TESTS_REQUIRED = 3
TOTAL_QUESTIONS = 25

DOMAIN_QUOTAS = {
    "aptitude": 10,
    "technical": 15,
}

DIFFICULTIES = ["easy", "medium", "hard"]
MAX_TOPIC_RATIO = 0.30
MAX_PER_TOPIC = int(TOTAL_QUESTIONS * MAX_TOPIC_RATIO)  # 7

# Adaptive selection: target success-probability window
ADAPTIVE_TARGET_LOW = 0.45
ADAPTIVE_TARGET_HIGH = 0.75

# Test duration
TEST_DURATION_MINUTES = 45          # both calibration and adaptive
TEST_DURATION_SECONDS = TEST_DURATION_MINUTES * 60
