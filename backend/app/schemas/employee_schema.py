# ─────────────────────────────────────────────────────────────────────────────
#  employee_schema.py  —  Pydantic request / response models
#
#  Key change from Chapter 1:
#    id is now a  str  (MongoDB ObjectId as hex string)
#    instead of an int (in-memory auto-increment counter).
# ─────────────────────────────────────────────────────────────────────────────
from pydantic import BaseModel
from typing import Optional


class EmployeeCreate(BaseModel):
    """Fields required when creating a new employee  (POST /employees)."""
    name: str
    email: str
    role: str
    department: str


class EmployeeUpdate(BaseModel):
    """
    Fields allowed for a partial update  (PUT /employees/{id}).
    Every field is Optional — only the ones sent by the client are changed.
    """
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None


class EmployeeResponse(BaseModel):
    """
    Shape returned to the client for any employee-related response.

    'id' is a string here because MongoDB's ObjectId is serialised as a
    24-character hex string  e.g.  "664f1a2b3c4d5e6f7a8b9c0d"
    """
    id: str
    name: str
    email: str
    role: str
    department: str
