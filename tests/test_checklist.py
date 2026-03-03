"""
Tests for the verification checklist endpoints:
  GET  /cases/{case_id}/checklist
  PATCH /cases/{case_id}/checklist

All tests mock the database session via FastAPI's dependency override mechanism
so no live database is required. Follows the project's TDD conventions:
  - unittest.mock for mocking
  - TestClient for HTTP assertions
  - Docstrings on every test
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.db import Case, get_session
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_case(checklist_json=None) -> MagicMock:
    """Return a minimal Case mock stub with the given checklist_json.

    Uses MagicMock(spec=Case) rather than Case.__new__(Case) so that
    SQLAlchemy's InstrumentedAttribute descriptors are never invoked —
    Case.__new__ leaves descriptor.impl as None, which raises
    AttributeError on any attribute read/write inside a route handler.
    """
    from datetime import datetime, timezone
    case = MagicMock(spec=Case)
    case.id = "test-case-001"
    case.client_id = "Client #0001"
    case.category = "Institutional Delay"
    case.complaint = "Test complaint for checklist unit tests."
    case.status = "investigated"
    case.result_json = None
    case.checklist_json = checklist_json
    case.action_taken = None
    case.department = None
    case.created_at = datetime.now(timezone.utc)
    case.resolved_at = None
    return case


def _override_session(case: Case | None):
    """Return a FastAPI dependency override that yields a mock session returning `case`."""
    async def _get_mock_session():
        session = AsyncMock()
        session.get = AsyncMock(return_value=case)
        yield session
    return _get_mock_session


# ---------------------------------------------------------------------------
# GET /cases/{case_id}/checklist
# ---------------------------------------------------------------------------

class TestGetCaseChecklist(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_returns_empty_dict_when_checklist_json_is_null(self):
        """GET returns {"checklist": {}} when checklist_json is null on the case."""
        app.dependency_overrides[get_session] = _override_session(_make_case(checklist_json=None))

        response = self.client.get("/cases/test-case-001/checklist")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"checklist": {}})

    def test_returns_existing_checklist_when_populated(self):
        """GET returns the persisted checklist dict when checklist_json is set."""
        saved = {
            "Confirm exact transfer initiation date with client": True,
            "Verify institution has received WS transfer request": False,
        }
        app.dependency_overrides[get_session] = _override_session(
            _make_case(checklist_json=saved)
        )

        response = self.client.get("/cases/test-case-001/checklist")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checklist"], saved)

    def test_returns_404_for_unknown_case_id(self):
        """GET returns 404 when no case matches the given case_id."""
        app.dependency_overrides[get_session] = _override_session(None)

        response = self.client.get("/cases/does-not-exist/checklist")

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())


# ---------------------------------------------------------------------------
# PATCH /cases/{case_id}/checklist
# ---------------------------------------------------------------------------

class TestPatchCaseChecklist(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_replaces_full_checklist_and_returns_updated_state(self):
        """PATCH persists the submitted checklist and echoes it back."""
        case = _make_case(checklist_json=None)
        app.dependency_overrides[get_session] = _override_session(case)

        payload = {
            "checklist": {
                "Confirm exact transfer initiation date with client": True,
                "Verify institution has received WS transfer request": True,
                "Check if securities require liquidation before transfer": False,
                "Confirm no prior failed attempts for this account": False,
            }
        }

        response = self.client.patch("/cases/test-case-001/checklist", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checklist"], payload["checklist"])
        # ORM attribute was updated in-place
        self.assertEqual(case.checklist_json, payload["checklist"])

    def test_returns_404_for_unknown_case_id(self):
        """PATCH returns 404 when no case matches the given case_id."""
        app.dependency_overrides[get_session] = _override_session(None)

        response = self.client.patch(
            "/cases/does-not-exist/checklist",
            json={"checklist": {"some item": True}},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    def test_handles_empty_checklist_dict(self):
        """PATCH accepts and stores an empty dict without error."""
        case = _make_case(checklist_json={"some item": True})
        app.dependency_overrides[get_session] = _override_session(case)

        response = self.client.patch(
            "/cases/test-case-001/checklist",
            json={"checklist": {}},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checklist"], {})

    def test_partial_checklist_stored_as_is(self):
        """PATCH stores whatever dict is submitted — partial or full — without validation."""
        case = _make_case(checklist_json=None)
        app.dependency_overrides[get_session] = _override_session(case)

        partial = {"Confirm exact transfer initiation date with client": True}
        response = self.client.patch(
            "/cases/test-case-001/checklist",
            json={"checklist": partial},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checklist"], partial)

    def test_overwrites_existing_checklist_on_second_patch(self):
        """PATCH replaces the entire previous checklist, not merging with it."""
        existing = {"Confirm exact transfer initiation date with client": True}
        case = _make_case(checklist_json=existing)
        app.dependency_overrides[get_session] = _override_session(case)

        new_payload = {"Verify institution has received WS transfer request": False}
        response = self.client.patch(
            "/cases/test-case-001/checklist",
            json={"checklist": new_payload},
        )

        self.assertEqual(response.status_code, 200)
        # Old key must be gone — full replacement, not merge
        result = response.json()["checklist"]
        self.assertNotIn("Confirm exact transfer initiation date with client", result)
        self.assertEqual(result, new_payload)


if __name__ == "__main__":
    unittest.main()
