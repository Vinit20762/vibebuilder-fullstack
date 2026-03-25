# ─────────────────────────────────────────────────────────────────────────────
#  conftest.py  —  Shared pytest fixtures
# ─────────────────────────────────────────────────────────────────────────────
import os
os.environ["DB_NAME"] = "company_db_test"   # must be before any app import

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.main import app

# ── Direct pymongo connection for fixtures ────────────────────────────────────
MONGO_URI       = os.getenv("MONGO_URI", "mongodb://localhost:27017")
_mongo_client   = MongoClient(MONGO_URI)
test_collection = _mongo_client["company_db_test"]["employees"]

SAMPLE_EMPLOYEES = [
    {"name": "John Doe",    "email": "john@test.com",   "role": "Engineer",  "department": "IT"},
    {"name": "Sarah Lee",   "email": "sarah@test.com",  "role": "Manager",   "department": "HR"},
    {"name": "Mike Ross",   "email": "mike@test.com",   "role": "Analyst",   "department": "Finance"},
    {"name": "Emily Clark", "email": "emily@test.com",  "role": "Developer", "department": "IT"},
    {"name": "David Kim",   "email": "david@test.com",  "role": "Designer",  "department": "Marketing"},
]


# ── HTTP client (session-scoped — created once for all tests) ─────────────────
@pytest.fixture(scope="session")
def http_client():
    with TestClient(app) as client:
        yield client


# ── Auth header fixtures ──────────────────────────────────────────────────────
# Tokens are fetched ONCE per session (session-scoped).
# Tokens are valid for 30 minutes — more than enough for a test run.

@pytest.fixture(scope="session")
def admin_headers(http_client):
    """Logs in as admin and returns the Authorization header dict."""
    response = http_client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, "Admin login failed during test setup"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def user_headers(http_client):
    """Logs in as regular user and returns the Authorization header dict."""
    response = http_client.post(
        "/auth/login",
        data={"username": "user", "password": "user123"},
    )
    assert response.status_code == 200, "User login failed during test setup"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── DB reset (function-scoped — runs before every single test) ────────────────
@pytest.fixture(autouse=True)
def reset_db():
    """Wipe and re-seed the test collection before every test."""
    test_collection.delete_many({})
    test_collection.insert_many([{**emp} for emp in SAMPLE_EMPLOYEES])
    yield
    test_collection.delete_many({})
