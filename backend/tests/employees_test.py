# ─────────────────────────────────────────────────────────────────────────────
#  employees_test.py  —  Integration tests with JWT authentication
#
#  All requests now require a valid Bearer token.
#  admin_headers → used for POST, PUT, DELETE (admin-only routes)
#  user_headers  → used for GET routes (any authenticated user)
#
#  Run:
#    pytest tests/employees_test.py -v
# ─────────────────────────────────────────────────────────────────────────────
import os
import pytest
from bson import ObjectId
from pymongo import MongoClient

MONGO_URI      = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_collection  = MongoClient(MONGO_URI)["company_db_test"]["employees"]


# =============================================================================
#  Auth — login + token validation
# =============================================================================
class TestAuthentication:

    def test_admin_login_returns_token(self, http_client):
        response = http_client.post(
            "/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_user_login_returns_token(self, http_client):
        response = http_client.post(
            "/auth/login",
            data={"username": "user", "password": "user123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_wrong_password_returns_401(self, http_client):
        response = http_client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_nonexistent_user_returns_401(self, http_client):
        response = http_client.post(
            "/auth/login",
            data={"username": "ghost", "password": "ghost123"},
        )
        assert response.status_code == 401

    def test_request_without_token_returns_401(self, http_client):
        # No Authorization header — should be rejected
        response = http_client.get("/employees")
        assert response.status_code == 401

    def test_request_with_invalid_token_returns_401(self, http_client):
        response = http_client.get(
            "/employees",
            headers={"Authorization": "Bearer this.is.not.a.valid.token"},
        )
        assert response.status_code == 401

    def test_user_role_cannot_create_employee_returns_403(self, http_client, user_headers):
        # user role → admin-only POST → 403 Forbidden
        response = http_client.post(
            "/employees",
            json={"name": "X", "email": "x@test.com", "role": "Dev", "department": "IT"},
            headers=user_headers,
        )
        assert response.status_code == 403

    def test_user_role_cannot_delete_employee_returns_403(self, http_client, user_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        response = http_client.delete(
            f"/employees/{emp['_id']}",
            headers=user_headers,
        )
        assert response.status_code == 403

    def test_user_role_cannot_update_employee_returns_403(self, http_client, user_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        response = http_client.put(
            f"/employees/{emp['_id']}",
            json={"role": "Hacker"},
            headers=user_headers,
        )
        assert response.status_code == 403

    def test_user_role_can_read_employees(self, http_client, user_headers):
        # user role CAN access GET endpoints
        response = http_client.get("/employees", headers=user_headers)
        assert response.status_code == 200


# =============================================================================
#  Feature 1 — Filter employees by department
# =============================================================================
class TestFilterByDepartment:

    def test_returns_only_it_employees(self, http_client, user_headers):
        response = http_client.get("/employees?department=IT", headers=user_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(e["department"] == "IT" for e in data)

    def test_returns_empty_list_for_nonexistent_department(self, http_client, user_headers):
        response = http_client.get("/employees?department=Legal", headers=user_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_employees_in_same_department(self, http_client, user_headers):
        response = http_client.get("/employees?department=HR", headers=user_headers)

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Sarah Lee"

    def test_department_filter_is_case_insensitive(self, http_client, user_headers):
        response = http_client.get("/employees?department=it", headers=user_headers)

        assert response.status_code == 200
        assert len(response.json()) == 2


# =============================================================================
#  Feature 2 — Search employees by name
# =============================================================================
class TestSearchByName:

    def test_exact_name_match(self, http_client, user_headers):
        response = http_client.get("/employees?name=John Doe", headers=user_headers)

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "John Doe"

    def test_partial_name_match(self, http_client, user_headers):
        response = http_client.get("/employees?name=john", headers=user_headers)

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_name_search_is_case_insensitive(self, http_client, user_headers):
        response = http_client.get("/employees?name=SARAH", headers=user_headers)

        assert response.status_code == 200
        assert response.json()[0]["name"] == "Sarah Lee"

    def test_no_match_returns_empty_list(self, http_client, user_headers):
        response = http_client.get("/employees?name=XYZNobody", headers=user_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_combined_name_and_department_filter(self, http_client, user_headers):
        response = http_client.get(
            "/employees?name=John&department=IT", headers=user_headers
        )

        assert response.status_code == 200
        assert len(response.json()) == 1


# =============================================================================
#  Feature 3 — Prevent duplicate email
# =============================================================================
class TestDuplicateEmail:

    def test_create_employee_with_unique_email_succeeds(self, http_client, admin_headers):
        response = http_client.post(
            "/employees",
            json={"name": "New Employee", "email": "new@test.com", "role": "Dev", "department": "IT"},
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["email"] == "new@test.com"

    def test_create_employee_with_duplicate_email_returns_400(self, http_client, admin_headers):
        response = http_client.post(
            "/employees",
            json={"name": "Another", "email": "john@test.com", "role": "Mgr", "department": "HR"},
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_duplicate_email_check_is_case_insensitive(self, http_client, admin_headers):
        response = http_client.post(
            "/employees",
            json={"name": "Another", "email": "JOHN@TEST.COM", "role": "Mgr", "department": "HR"},
            headers=admin_headers,
        )
        assert response.status_code == 400


# =============================================================================
#  Feature 4 — Validate required fields
# =============================================================================
class TestRequiredFieldValidation:

    BASE = {
        "name": "Test Employee",
        "email": "uniquetest@test.com",
        "role": "Engineer",
        "department": "IT",
    }

    def test_missing_name_returns_422(self, http_client, admin_headers):
        payload = {k: v for k, v in self.BASE.items() if k != "name"}
        response = http_client.post("/employees", json=payload, headers=admin_headers)
        assert response.status_code == 422

    def test_missing_email_returns_422(self, http_client, admin_headers):
        payload = {k: v for k, v in self.BASE.items() if k != "email"}
        response = http_client.post("/employees", json=payload, headers=admin_headers)
        assert response.status_code == 422

    def test_missing_role_returns_422(self, http_client, admin_headers):
        payload = {k: v for k, v in self.BASE.items() if k != "role"}
        response = http_client.post("/employees", json=payload, headers=admin_headers)
        assert response.status_code == 422

    def test_missing_department_returns_422(self, http_client, admin_headers):
        payload = {k: v for k, v in self.BASE.items() if k != "department"}
        response = http_client.post("/employees", json=payload, headers=admin_headers)
        assert response.status_code == 422

    def test_blank_name_returns_400(self, http_client, admin_headers):
        response = http_client.post(
            "/employees",
            json={"name": "   ", "email": "blank@test.com", "role": "Eng", "department": "IT"},
            headers=admin_headers,
        )
        assert response.status_code == 400

    def test_invalid_email_format_returns_400(self, http_client, admin_headers):
        response = http_client.post(
            "/employees",
            json={"name": "Test", "email": "not-an-email", "role": "Eng", "department": "IT"},
            headers=admin_headers,
        )
        assert response.status_code == 400


# =============================================================================
#  Feature 5 — Summary endpoint
# =============================================================================
class TestSummaryEndpoint:

    def test_returns_correct_total_count(self, http_client, user_headers):
        response = http_client.get("/employees/summary", headers=user_headers)

        assert response.status_code == 200
        assert response.json()["total_employees"] == 5

    def test_returns_correct_unique_departments(self, http_client, user_headers):
        response = http_client.get("/employees/summary", headers=user_headers)

        assert response.status_code == 200
        assert set(response.json()["departments"]) == {"IT", "HR", "Finance", "Marketing"}

    def test_departments_have_no_duplicates(self, http_client, user_headers):
        response = http_client.get("/employees/summary", headers=user_headers)
        departments = response.json()["departments"]
        assert len(departments) == len(set(departments))

    def test_departments_are_sorted_alphabetically(self, http_client, user_headers):
        response = http_client.get("/employees/summary", headers=user_headers)
        departments = response.json()["departments"]
        assert departments == sorted(departments)

    def test_summary_updates_after_adding_employee(self, http_client, admin_headers):
        http_client.post(
            "/employees",
            json={"name": "Extra", "email": "extra@test.com", "role": "Tester", "department": "QA"},
            headers=admin_headers,
        )
        response = http_client.get("/employees/summary", headers=admin_headers)
        assert response.json()["total_employees"] == 6
        assert "QA" in response.json()["departments"]

    def test_summary_updates_after_deleting_employee(self, http_client, admin_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        http_client.delete(f"/employees/{emp['_id']}", headers=admin_headers)

        response = http_client.get("/employees/summary", headers=admin_headers)
        assert response.json()["total_employees"] == 4


# =============================================================================
#  GET /employees/{id}
# =============================================================================
class TestGetEmployeeById:

    def test_returns_correct_employee(self, http_client, user_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        response = http_client.get(f"/employees/{emp_id}", headers=user_headers)

        assert response.status_code == 200
        assert response.json()["name"] == "John Doe"
        assert response.json()["id"] == emp_id

    def test_returns_404_for_nonexistent_id(self, http_client, user_headers):
        response = http_client.get(f"/employees/{ObjectId()}", headers=user_headers)
        assert response.status_code == 404

    def test_returns_400_for_invalid_id_format(self, http_client, user_headers):
        response = http_client.get("/employees/not-a-valid-id", headers=user_headers)
        assert response.status_code == 400


# =============================================================================
#  DELETE /employees/{id}
# =============================================================================
class TestDeleteEmployee:

    def test_delete_returns_success_message(self, http_client, admin_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        response = http_client.delete(f"/employees/{emp['_id']}", headers=admin_headers)

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_deleted_employee_no_longer_retrievable(self, http_client, admin_headers, user_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        http_client.delete(f"/employees/{emp_id}", headers=admin_headers)

        response = http_client.get(f"/employees/{emp_id}", headers=user_headers)
        assert response.status_code == 404

    def test_delete_nonexistent_employee_returns_404(self, http_client, admin_headers):
        response = http_client.delete(f"/employees/{ObjectId()}", headers=admin_headers)
        assert response.status_code == 404


# =============================================================================
#  PUT /employees/{id}
# =============================================================================
class TestUpdateEmployee:

    def test_update_single_field_leaves_others_unchanged(self, http_client, admin_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        response = http_client.put(
            f"/employees/{emp['_id']}",
            json={"role": "Senior Engineer"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "Senior Engineer"
        assert response.json()["name"] == "John Doe"
        assert response.json()["department"] == "IT"

    def test_update_multiple_fields(self, http_client, admin_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        response = http_client.put(
            f"/employees/{emp['_id']}",
            json={"role": "Lead", "department": "Engineering"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["role"] == "Lead"
        assert response.json()["department"] == "Engineering"

    def test_update_nonexistent_employee_returns_404(self, http_client, admin_headers):
        response = http_client.put(
            f"/employees/{ObjectId()}",
            json={"role": "Engineer"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    def test_update_email_to_duplicate_returns_400(self, http_client, admin_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        response = http_client.put(
            f"/employees/{emp['_id']}",
            json={"email": "sarah@test.com"},
            headers=admin_headers,
        )
        assert response.status_code == 400

    def test_employee_can_keep_own_email_on_update(self, http_client, admin_headers):
        emp = db_collection.find_one({"name": "John Doe"})
        response = http_client.put(
            f"/employees/{emp['_id']}",
            json={"email": "john@test.com", "role": "Lead"},
            headers=admin_headers,
        )
        assert response.status_code == 200
