# ─────────────────────────────────────────────────────────────────────────────
#  employee_controller.py  —  Business logic layer (MongoDB edition)
#
#  All database operations go through pymongo here.
#  The route layer calls these functions and returns the result directly.
# ─────────────────────────────────────────────────────────────────────────────
import re
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.config.database import employee_collection
from app.schemas.employee_schema import EmployeeCreate, EmployeeUpdate


# ── Helper: MongoDB document → clean dict ─────────────────────────────────────
def _to_response(doc: dict) -> dict:
    """
    MongoDB stores the primary key as '_id' (an ObjectId object).
    The API exposes it as 'id' (a plain string).
    This helper converts every raw document before returning it to the caller.
    """
    doc["id"] = str(doc.pop("_id"))   # ObjectId → str,  rename _id → id
    return doc


# ── Helper: parse & validate ObjectId string ─────────────────────────────────
def _parse_oid(employee_id: str) -> ObjectId:
    """
    Converts the string id from the URL into a BSON ObjectId.
    Raises 400 if the string is not a valid 24-char hex ObjectId.
    """
    try:
        return ObjectId(employee_id)
    except (InvalidId, Exception):
        raise HTTPException(
            status_code=400,
            detail=f"'{employee_id}' is not a valid employee id. "
                   f"Expected a 24-character hex string.",
        )


# ── Helper: basic email format check ─────────────────────────────────────────
def _validate_email(email: str) -> None:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(pattern, email):
        raise HTTPException(status_code=400, detail=f"Invalid email format: '{email}'")


# ── Helper: duplicate email check ────────────────────────────────────────────
def _check_duplicate_email(email: str, exclude_id: Optional[ObjectId] = None) -> None:
    """
    Queries MongoDB for a document with the same email (case-insensitive).
    exclude_id is passed during updates so the employee can keep their own email.
    """
    query: dict = {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
    if exclude_id:
        query["_id"] = {"$ne": exclude_id}   # $ne = "not equal"

    if employee_collection.find_one(query):
        raise HTTPException(
            status_code=400,
            detail=f"Email '{email}' is already registered to another employee.",
        )


# ── Public controller functions ───────────────────────────────────────────────

def list_employees(
    department: Optional[str] = None,
    role: Optional[str] = None,
    name: Optional[str] = None,
) -> List[dict]:
    """
    Returns all employees.  Filters are applied as MongoDB queries (server-side),
    which is more efficient than fetching everything and filtering in Python.

    department / role  →  exact match, case-insensitive
    name               →  partial match, case-insensitive  ("joh" matches "John Doe")
    """
    query: dict = {}

    if department:
        # ^…$ anchors make it a full-word match (not partial)
        query["department"] = {"$regex": f"^{re.escape(department)}$", "$options": "i"}

    if role:
        query["role"] = {"$regex": f"^{re.escape(role)}$", "$options": "i"}

    if name:
        # No anchors — partial match anywhere in the name
        query["name"] = {"$regex": re.escape(name), "$options": "i"}

    docs = list(employee_collection.find(query))
    return [_to_response(doc) for doc in docs]


def get_employee(employee_id: str) -> dict:
    """Fetches a single employee by ObjectId. Raises 404 if not found."""
    oid = _parse_oid(employee_id)
    doc = employee_collection.find_one({"_id": oid})

    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with id '{employee_id}' not found.",
        )
    return _to_response(doc)


def create_employee(data: EmployeeCreate) -> dict:
    """
    Validates and inserts a new employee document into MongoDB.

    Validation:
      • name must not be blank
      • email must have valid format
      • email must be unique
    """
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    _validate_email(data.email)
    _check_duplicate_email(data.email)

    new_doc = {
        "name":       data.name.strip(),
        "email":      data.email.lower().strip(),
        "role":       data.role.strip(),
        "department": data.department.strip(),
    }

    # insert_one mutates new_doc in-place, adding the '_id' key
    result = employee_collection.insert_one(new_doc)

    # Fetch the freshly inserted document so we return exactly what's in DB
    inserted = employee_collection.find_one({"_id": result.inserted_id})
    return _to_response(inserted)


def update_employee(employee_id: str, data: EmployeeUpdate) -> dict:
    """
    Partially updates an employee in MongoDB.

    model_dump(exclude_unset=True) gives us only the fields the client sent.
    We pass those directly to MongoDB's $set operator — untouched fields
    remain unchanged in the database.
    """
    oid = _parse_oid(employee_id)

    # Confirm the employee exists before trying to update
    existing = employee_collection.find_one({"_id": oid})
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with id '{employee_id}' not found.",
        )

    updates = data.model_dump(exclude_unset=True)   # only fields the client sent

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    # Validate only the fields that were actually sent
    if "name" in updates and not updates["name"].strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    if "email" in updates:
        _validate_email(updates["email"])
        _check_duplicate_email(updates["email"], exclude_id=oid)
        updates["email"] = updates["email"].lower().strip()

    # Strip whitespace from any string fields
    updates = {k: v.strip() if isinstance(v, str) else v for k, v in updates.items()}

    # $set updates ONLY the specified fields; everything else stays as-is
    employee_collection.update_one({"_id": oid}, {"$set": updates})

    updated = employee_collection.find_one({"_id": oid})
    return _to_response(updated)


def delete_employee(employee_id: str) -> dict:
    """
    Deletes an employee document from MongoDB.
    Returns a success message, or raises 404 if not found.
    """
    oid = _parse_oid(employee_id)
    doc = employee_collection.find_one({"_id": oid})

    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with id '{employee_id}' not found.",
        )

    employee_collection.delete_one({"_id": oid})
    return {"message": f"Employee '{doc['name']}' deleted successfully."}


def get_summary() -> dict:
    """
    Returns a summary of the employee collection:
      - total number of employees
      - list of unique departments (no duplicates)

    Uses MongoDB's count_documents() and distinct() — both are single
    efficient queries rather than loading all documents into Python.
    """
    total = employee_collection.count_documents({})
    departments = employee_collection.distinct("department")

    return {
        "total_employees": total,
        "departments": sorted(departments),   # sorted for consistent ordering
    }
