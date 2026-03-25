# ─────────────────────────────────────────────────────────────────────────────
#  database.py  —  MongoDB connection + collection handle
#
#  This file is responsible for ONE thing: give the rest of the app a ready-to-
#  use MongoDB collection object.
#
#  Config is read from .env so we never hard-code credentials in source code.
# ─────────────────────────────────────────────────────────────────────────────
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load variables from the .env file into os.environ
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME",   "company_db")

# Create a single MongoClient for the whole application.
# pymongo handles connection pooling internally — one client is enough.
client = MongoClient(MONGO_URI)

# The database object (equivalent to "USE company_db" in mongosh)
database = client[DB_NAME]

# The collection we will query in every controller function.
# Equivalent to a table in a relational database.
employee_collection = database["employees"]


# ── Seed data ─────────────────────────────────────────────────────────────────
# Called once on startup (from main.py lifespan).
# Inserts sample employees ONLY if the collection is empty, so re-starting the
# server never duplicates records.
SAMPLE_EMPLOYEES = [
    {"name": "John Doe",    "email": "john@test.com",    "role": "Engineer",  "department": "IT"},
    {"name": "Sarah Lee",   "email": "sarah@test.com",   "role": "Manager",   "department": "HR"},
    {"name": "Mike Ross",   "email": "mike@test.com",    "role": "Analyst",   "department": "Finance"},
    {"name": "Emily Clark", "email": "emily@test.com",   "role": "Developer", "department": "IT"},
    {"name": "David Kim",   "email": "david@test.com",   "role": "Designer",  "department": "Marketing"},
]


def seed_database() -> None:
    """Insert sample employees if the collection is currently empty."""
    if employee_collection.count_documents({}) == 0:
        employee_collection.insert_many(SAMPLE_EMPLOYEES)
        print(f"[seed] Inserted {len(SAMPLE_EMPLOYEES)} sample employees into '{DB_NAME}.employees'")
    else:
        print(f"[seed] Collection already has data — skipping seed.")
