# ─────────────────────────────────────────────────────────────────────────────
#  employee_routes.py  —  Route definitions
#
#  Only change from the in-memory version:
#    employee_id type is now  str  (MongoDB ObjectId) instead of  int.
# ─────────────────────────────────────────────────────────────────────────────
from typing import List, Optional

from fastapi import APIRouter, Query

from app.schemas.employee_schema import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
)
from app.controller import employee_controller as ctrl

router = APIRouter(prefix="/employees", tags=["Employees"])


# ── GET /employees  (list + filter) ──────────────────────────────────────────
@router.get("", response_model=List[EmployeeResponse])
def list_employees(
    department: Optional[str] = Query(None, description="Filter by department  e.g. IT"),
    role:       Optional[str] = Query(None, description="Filter by role  e.g. Engineer"),
    name:       Optional[str] = Query(None, description="Partial name search  e.g. John"),
):
    return ctrl.list_employees(department=department, role=role, name=name)


# ── POST /employees  (create) ─────────────────────────────────────────────────
@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(data: EmployeeCreate):
    return ctrl.create_employee(data)


# ── GET /employees/summary  ────────────────────────────────────────────────────
# IMPORTANT: This route MUST be defined before /{employee_id}.
# If it came after, FastAPI would match /employees/summary against the
# /{employee_id} pattern and treat "summary" as an employee id → 400 error.
@router.get("/summary", tags=["Employees"])
def get_summary():
    """Returns total employee count and list of unique departments."""
    return ctrl.get_summary()


# ── GET /employees/{id}  (get one) ────────────────────────────────────────────
@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: str):
    return ctrl.get_employee(employee_id)


# ── PUT /employees/{id}  (partial update) ─────────────────────────────────────
@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: str, data: EmployeeUpdate):
    return ctrl.update_employee(employee_id, data)


# ── DELETE /employees/{id}  (delete) ──────────────────────────────────────────
@router.delete("/{employee_id}")
def delete_employee(employee_id: str):
    return ctrl.delete_employee(employee_id)
