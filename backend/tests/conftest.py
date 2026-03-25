# ─────────────────────────────────────────────────────────────────────────────
#  conftest.py  —  Shared pytest fixtures for all test files
#
#  CRITICAL: The os.environ line MUST stay at the very top, before any import
#  that touches the app.  database.py runs its connection code at import time,
#  so the env var must already be set when Python first loads that module.
#
#  load_dotenv() (inside database.py) does NOT override an env var that is
#  already present in os.environ — so our test value wins.
# ─────────────────────────────────────────────────────────────────────────────
import os
os.environ["DB_NAME"] = "company_db_test"   # ← must be line 1 of real code

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.main import app

# ── Direct pymongo connection used only by fixtures (not by the app) ──────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
_mongo_client   = MongoClient(MONGO_URI)
test_collection = _mongo_client["company_db_test"]["employees"]

# ── Known sample data — inserted fresh before every test ─────────────────────
SAMPLE_EMPLOYEES = [
    {"name": "John Doe",    "email": "john@test.com",   "role": "Engineer",  "department": "IT"},
    {"name": "Sarah Lee",   "email": "sarah@test.com",  "role": "Manager",   "department": "HR"},
    {"name": "Mike Ross",   "email": "mike@test.com",   "role": "Analyst",   "department": "Finance"},
    {"name": "Emily Clark", "email": "emily@test.com",  "role": "Developer", "department": "IT"},
    {"name": "David Kim",   "email": "david@test.com",  "role": "Designer",  "department": "Marketing"},
]


@pytest.fixture(scope="session")
def http_client():
    """
    One TestClient for the whole test session.
    Using 'with' triggers the FastAPI lifespan once:
      startup  → seed_database() runs → seeds test DB if empty
      shutdown → nothing to clean up
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def reset_db():
    """
    Runs automatically before EVERY test (autouse=True).

    Guarantees each test starts with exactly the same 5 known employees.
    Without this, a test that creates or deletes an employee would pollute
    the next test's data.

    {**emp} creates a shallow copy so pymongo's insert_many() doesn't mutate
    the original SAMPLE_EMPLOYEES list by adding '_id' keys to those dicts.
    """
    test_collection.delete_many({})
    test_collection.insert_many([{**emp} for emp in SAMPLE_EMPLOYEES])
    yield
    test_collection.delete_many({})   # clean up after test completes
