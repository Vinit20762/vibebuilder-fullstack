# ─────────────────────────────────────────────────────────────────────────────
#  employees_test.py  —  Real-DB integration tests (no mocks)
#
#  Every test hits a real MongoDB instance using the 'company_db_test' database.
#  The conftest.py reset_db fixture wipes and reseeds the collection before
#  each test so every test starts with exactly 5 known employees.
#
#  Run:
#    pytest tests/employees_test.py -v
#
#  Requirements:
#    • MongoDB must be running on localhost:27017
#    • pip install -r requirements.txt
# ─────────────────────────────────────────────────────────────────────────────
import os
import pytest
from bson import ObjectId
from pymongo import MongoClient

# Direct connection to the test collection — used only to look up real ObjectIds
# in tests that need to pass an id to an endpoint.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_collection = MongoClient(MONGO_URI)["company_db_test"]["employees"]


# =============================================================================
#  Feature 1 — Filter employees by department
#  Endpoint: GET /employees?department=IT
# =============================================================================
class TestFilterByDepartment:

    def test_returns_only_it_employees(self, http_client):
        response = http_client.get("/employees?department=IT")

        assert response.status_code == 200
        data = response.json()
        # Sample data: John Doe (IT) + Emily Clark (IT) = 2
        assert len(data) == 2
        assert all(e["department"] == "IT" for e in data)

    def test_returns_empty_list_for_nonexistent_department(self, http_client):
        response = http_client.get("/employees?department=Legal")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_employees_in_same_department(self, http_client):
        # HR has only Sarah Lee in sample data
        response = http_client.get("/employees?department=HR")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Sarah Lee"

    def test_department_filter_is_case_insensitive(self, http_client):
        # "it" (lowercase) should match "IT"
        response = http_client.get("/employees?department=it")

        assert response.status_code == 200
        assert len(response.json()) == 2


# =============================================================================
#  Feature 2 — Search employees by name
#  Endpoint: GET /employees?name=John
# =============================================================================
class TestSearchByName:

    def test_exact_name_match(self, http_client):
        response = http_client.get("/employees?name=John Doe")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "John Doe"

    def test_partial_name_match(self, http_client):
        # "john" is a partial match for "John Doe"
        response = http_client.get("/employees?name=john")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "John Doe"

    def test_name_search_is_case_insensitive(self, http_client):
        # "SARAH" should match "Sarah Lee"
        response = http_client.get("/employees?name=SARAH")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "Sarah Lee"

    def test_no_match_returns_empty_list(self, http_client):
        response = http_client.get("/employees?name=XYZNobody")

        assert response.status_code == 200
        assert response.json() == []

    def test_combined_name_and_department_filter(self, http_client):
        # "John" in "IT" → only John Doe matches both
        response = http_client.get("/employees?name=John&department=IT")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == "John Doe"


# =============================================================================
#  Feature 3 — Prevent duplicate email
#  Endpoint: POST /employees
# =============================================================================
class TestDuplicateEmail:

    def test_create_employee_with_unique_email_succeeds(self, http_client):
        response = http_client.post("/employees", json={
            "name": "New Employee",
            "email": "newemployee@test.com",   # not in sample data
            "role": "Developer",
            "department": "IT",
        })

        assert response.status_code == 201
        assert response.json()["email"] == "newemployee@test.com"

    def test_create_employee_with_duplicate_email_returns_400(self, http_client):
        # "john@test.com" already exists in sample data
        response = http_client.post("/employees", json={
            "name": "Another John",
            "email": "john@test.com",
            "role": "Manager",
            "department": "HR",
        })

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_duplicate_email_check_is_case_insensitive(self, http_client):
        # "JOHN@TEST.COM" is the same as "john@test.com"
        response = http_client.post("/employees", json={
            "name": "Another John",
            "email": "JOHN@TEST.COM",
            "role": "Manager",
            "department": "HR",
        })

        assert response.status_code == 400


# =============================================================================
#  Feature 4 — Validate required fields
#  Endpoint: POST /employees
# =============================================================================
class TestRequiredFieldValidation:

    BASE = {
        "name": "Test Employee",
        "email": "uniquetest@test.com",
        "role": "Engineer",
        "department": "IT",
    }

    def test_missing_name_returns_422(self, http_client):
        # 422 = Pydantic validation error — field is completely absent
        payload = {k: v for k, v in self.BASE.items() if k != "name"}
        response = http_client.post("/employees", json=payload)
        assert response.status_code == 422

    def test_missing_email_returns_422(self, http_client):
        payload = {k: v for k, v in self.BASE.items() if k != "email"}
        response = http_client.post("/employees", json=payload)
        assert response.status_code == 422

    def test_missing_role_returns_422(self, http_client):
        payload = {k: v for k, v in self.BASE.items() if k != "role"}
        response = http_client.post("/employees", json=payload)
        assert response.status_code == 422

    def test_missing_department_returns_422(self, http_client):
        payload = {k: v for k, v in self.BASE.items() if k != "department"}
        response = http_client.post("/employees", json=payload)
        assert response.status_code == 422

    def test_blank_name_returns_400(self, http_client):
        # Pydantic accepts empty string (it IS a str) but controller rejects it
        response = http_client.post("/employees", json={
            "name": "   ",           # whitespace only
            "email": "blank@test.com",
            "role": "Engineer",
            "department": "IT",
        })

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_invalid_email_format_returns_400(self, http_client):
        response = http_client.post("/employees", json={
            "name": "Test User",
            "email": "not-an-email",  # missing @
            "role": "Engineer",
            "department": "IT",
        })

        assert response.status_code == 400
        assert "invalid email" in response.json()["detail"].lower()


# =============================================================================
#  Feature 5 — Employee summary endpoint
#  Endpoint: GET /employees/summary
# =============================================================================
class TestSummaryEndpoint:

    def test_returns_correct_total_count(self, http_client):
        # reset_db always seeds exactly 5 employees
        response = http_client.get("/employees/summary")

        assert response.status_code == 200
        assert response.json()["total_employees"] == 5

    def test_returns_correct_unique_departments(self, http_client):
        response = http_client.get("/employees/summary")

        assert response.status_code == 200
        # Sample data covers: IT, HR, Finance, Marketing
        assert set(response.json()["departments"]) == {"IT", "HR", "Finance", "Marketing"}

    def test_departments_have_no_duplicates(self, http_client):
        response = http_client.get("/employees/summary")
        departments = response.json()["departments"]

        # If duplicates exist, len(list) > len(set)
        assert len(departments) == len(set(departments))

    def test_departments_are_sorted_alphabetically(self, http_client):
        response = http_client.get("/employees/summary")
        departments = response.json()["departments"]

        assert departments == sorted(departments)

    def test_summary_updates_after_adding_new_employee(self, http_client):
        # Add a new employee in a new department
        http_client.post("/employees", json={
            "name": "Extra Employee",
            "email": "extra@test.com",
            "role": "Tester",
            "department": "QA",
        })

        response = http_client.get("/employees/summary")

        assert response.json()["total_employees"] == 6
        assert "QA" in response.json()["departments"]

    def test_summary_updates_after_deleting_employee(self, http_client):
        emp = db_collection.find_one({"name": "John Doe"})
        http_client.delete(f"/employees/{emp['_id']}")

        response = http_client.get("/employees/summary")

        assert response.json()["total_employees"] == 4


# =============================================================================
#  GET /employees/{id}
# =============================================================================
class TestGetEmployeeById:

    def test_returns_correct_employee(self, http_client):
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        response = http_client.get(f"/employees/{emp_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "John Doe"
        assert body["id"] == emp_id

    def test_returns_404_for_nonexistent_id(self, http_client):
        fake_id = str(ObjectId())   # valid format but not in DB
        response = http_client.get(f"/employees/{fake_id}")

        assert response.status_code == 404

    def test_returns_400_for_invalid_id_format(self, http_client):
        response = http_client.get("/employees/not-a-valid-id")

        assert response.status_code == 400


# =============================================================================
#  DELETE /employees/{id}
# =============================================================================
class TestDeleteEmployee:

    def test_delete_returns_success_message(self, http_client):
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        response = http_client.delete(f"/employees/{emp_id}")

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_deleted_employee_is_no_longer_retrievable(self, http_client):
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        http_client.delete(f"/employees/{emp_id}")
        response = http_client.get(f"/employees/{emp_id}")

        assert response.status_code == 404

    def test_delete_nonexistent_employee_returns_404(self, http_client):
        response = http_client.delete(f"/employees/{ObjectId()}")

        assert response.status_code == 404


# =============================================================================
#  PUT /employees/{id} — partial update
# =============================================================================
class TestUpdateEmployee:

    def test_update_single_field_leaves_others_unchanged(self, http_client):
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        response = http_client.put(
            f"/employees/{emp_id}",
            json={"role": "Senior Engineer"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "Senior Engineer"
        assert body["name"] == "John Doe"           # unchanged
        assert body["department"] == "IT"           # unchanged

    def test_update_multiple_fields(self, http_client):
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        response = http_client.put(
            f"/employees/{emp_id}",
            json={"role": "Lead", "department": "Engineering"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "Lead"
        assert body["department"] == "Engineering"

    def test_update_nonexistent_employee_returns_404(self, http_client):
        response = http_client.put(
            f"/employees/{ObjectId()}",
            json={"role": "Engineer"},
        )
        assert response.status_code == 404

    def test_update_email_to_existing_email_returns_400(self, http_client):
        # Try to change John's email to Sarah's email
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        response = http_client.put(
            f"/employees/{emp_id}",
            json={"email": "sarah@test.com"},
        )

        assert response.status_code == 400

    def test_employee_can_update_with_own_email(self, http_client):
        # Sending the same email back should NOT be treated as a duplicate
        emp = db_collection.find_one({"name": "John Doe"})
        emp_id = str(emp["_id"])

        response = http_client.put(
            f"/employees/{emp_id}",
            json={"email": "john@test.com", "role": "Lead"},
        )

        assert response.status_code == 200
