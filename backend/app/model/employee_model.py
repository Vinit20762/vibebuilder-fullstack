# ─────────────────────────────────────────────────────────────────────────────
#  employee_model.py  —  Internal data shape
#
#  With MongoDB, documents don't have a fixed schema enforced by the database.
#  We use Python's TypedDict to document the shape of each employee record
#  as it lives inside MongoDB (after we convert _id → id).
#
#  This is NOT enforced at runtime — it is purely for documentation and IDE
#  type-hint support.
# ─────────────────────────────────────────────────────────────────────────────
from typing import TypedDict


class Employee(TypedDict):
    """
    Shape of one employee document as returned by the controller.

    Note:
      - MongoDB stores the primary key as _id (ObjectId).
      - We always convert it to a plain string 'id' before returning to callers.
        The raw _id field is never exposed outside the controller layer.
    """
    id: str          # MongoDB ObjectId converted to string  e.g. "507f1f77bcf86cd799439011"
    name: str
    email: str
    role: str
    department: str
