"""
Integration test for FastAPI Cockpit trial limit enforcement (2-Run Model).
Tests:
- /api/trial-status endpoint (initial: 2 runs remaining)
- 1st /api/run -> 200 OK (1 remaining)
- 2nd /api/run -> 200 OK (0 remaining, locked)
- 3rd /api/run -> 403 Forbidden (Blocked)
- Bypass attempt via cleared cookies / curl -> 403 Forbidden (Blocked)
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

import serve_cockpit
from src.trial_limiter import TrialLimiter


@pytest.fixture
def client_with_isolated_limiter():
    temp_dir = tempfile.mkdtemp()
    ledger_file = os.path.join(temp_dir, "test_api_ledger_2runs.json")
    isolated_limiter = TrialLimiter(ledger_path=ledger_file, max_runs=2, max_subnet_runs=4)

    original_limiter = serve_cockpit.trial_limiter
    serve_cockpit.trial_limiter = isolated_limiter

    client = TestClient(serve_cockpit.app)
    yield client

    serve_cockpit.trial_limiter = original_limiter
    if os.path.exists(ledger_file):
        try:
            os.remove(ledger_file)
        except Exception:
            pass


def test_api_strict_two_runs_limit(client_with_isolated_limiter):
    client = client_with_isolated_limiter
    headers = {
        "X-Client-Fingerprint": "browser_hw_hash_two_runs",
        "User-Agent": "TestScientistBrowser/1.0"
    }

    # 1. Initial trial status check: 2 runs available
    resp = client.get("/api/trial-status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert data["runs_used"] == 0
    assert data["runs_remaining"] == 2
    assert data["max_runs"] == 2
    assert "bionemo_trial_session" in resp.cookies

    # 2. First Run -> 200 OK (1 remaining)
    resp1 = client.post("/api/run?target=KRAS+G12D&candidates=2", headers=headers)
    assert resp1.status_code == 200
    res1 = resp1.json()
    assert res1["status"] == "completed"
    assert res1["trial_status"]["runs_used"] == 1
    assert res1["trial_status"]["runs_remaining"] == 1
    assert res1["trial_status"]["is_locked"] is False

    # 3. Second Run -> 200 OK (0 remaining, locked)
    resp2 = client.post("/api/run?target=SARS-CoV-2+Mpro&candidates=2", headers=headers)
    assert resp2.status_code == 200
    res2 = resp2.json()
    assert res2["status"] == "completed"
    assert res2["trial_status"]["runs_used"] == 2
    assert res2["trial_status"]["runs_remaining"] == 0
    assert res2["trial_status"]["is_locked"] is True

    # 4. Third Run -> MUST BE 403 FORBIDDEN
    resp3 = client.post("/api/run?target=EGFR+T790M&candidates=2", headers=headers)
    assert resp3.status_code == 403
    res3 = resp3.json()
    assert res3["error"] == "TRIAL_LIMIT_EXCEEDED"
    assert res3["runs_used"] == 2
    assert res3["runs_remaining"] == 0

    # 5. Exploit attempt: Clear cookies (fresh client), same fingerprint
    fresh_client = TestClient(serve_cockpit.app)
    resp4 = fresh_client.post("/api/run?target=HER2&candidates=2", headers=headers)
    assert resp4.status_code == 403
    assert resp4.json()["error"] == "TRIAL_LIMIT_EXCEEDED"
