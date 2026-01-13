import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# App-level constants
CALIBRATION_TEST_COUNT = 3
DEFAULT_TEST_LENGTH = 25
