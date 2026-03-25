# ─────────────────────────────────────────────────────────────────────────────
#  employee_routes.py  —  Route definitions with JWT protection
#
#  Access rules:
#    GET  /employees          → any logged-in user  (get_current_user)
#    GET  /employees/summary  → any logged-in user  (get_current_user)
#    GET  /employees/{id}     → any logged-in user  (get_current_user)
#    POST /employees          → admin only           (require_admin)
#    PUT  /employees/{id}     → admin only           (require_admin)
#    DELETE /employees/{id}   → admin only           (require_admin)
#
#  How Depends() works:
#    FastAPI calls the dependency function BEFORE the route handler.
#    If it raises an exception (401/403), the route handler never runs.
#    If it succeeds, it returns the current_user dict to the route handler.
# ─────────────────────────────────────────────────────────────────────────────
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.auth.auth import get_current_user, require_admin
from app.controller import employee_controller as ctrl
from app.schemas.employee_schema import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


# ── GET /employees  (list + filter) ──────────────────────────────────────────
@router.get("", response_model=List[EmployeeResponse])
def list_employees(
    department: Optional[str] = Query(None, description="Filter by department  e.g. IT"),
    role:       Optional[str] = Query(None, description="Filter by role  e.g. Engineer"),
    name:       Optional[str] = Query(None, description="Partial name search  e.g. John"),
    current_user: dict = Depends(get_current_user),   # any authenticated user
):
    return ctrl.list_employees(department=department, role=role, name=name)


# ── POST /employees  (create) — admin only ────────────────────────────────────
@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(
    data: EmployeeCreate,
    current_user: dict = Depends(require_admin),       # admin only
):
    return ctrl.create_employee(data)


# ── GET /employees/summary  — any authenticated user ─────────────────────────
# MUST stay before /{employee_id} to avoid being matched as an id.
@router.get("/summary", tags=["Employees"])
def get_summary(
    current_user: dict = Depends(get_current_user),    # any authenticated user
):
    return ctrl.get_summary()


# ── GET /employees/{id}  (get one) — any authenticated user ──────────────────
@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: str,
    current_user: dict = Depends(get_current_user),    # any authenticated user
):
    return ctrl.get_employee(employee_id)


# ── PUT /employees/{id}  (partial update) — admin only ───────────────────────
@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    current_user: dict = Depends(require_admin),       # admin only
):
    return ctrl.update_employee(employee_id, data)


# ── DELETE /employees/{id}  (delete) — admin only ────────────────────────────
@router.delete("/{employee_id}")
def delete_employee(
    employee_id: str,
    current_user: dict = Depends(require_admin),       # admin only
):
    return ctrl.delete_employee(employee_id)
