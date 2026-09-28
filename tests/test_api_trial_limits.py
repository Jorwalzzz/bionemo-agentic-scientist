"""
Integration test for FastAPI Cockpit trial limit enforcement (Strict 1-Run Limit).
Tests:
- /api/trial-status endpoint (initial: 1 run remaining)
- 1st /api/run -> 200 OK
- 2nd /api/run -> 403 Forbidden (Blocked)
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
    ledger_file = os.path.join(temp_dir, "test_api_ledger_1run.json")
    isolated_limiter = TrialLimiter(ledger_path=ledger_file, max_runs=1, max_subnet_runs=2)

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


def test_api_strict_single_run_limit(client_with_isolated_limiter):
    client = client_with_isolated_limiter
    headers = {
        "X-Client-Fingerprint": "browser_hw_hash_single_run",
        "User-Agent": "TestScientistBrowser/1.0"
    }

    # 1. Initial trial status check: 1 run available
    resp = client.get("/api/trial-status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert data["runs_used"] == 0
    assert data["runs_remaining"] == 1
    assert data["max_runs"] == 1
    assert "bionemo_trial_session" in resp.cookies

    # 2. First and ONLY allowed run -> 200 OK
    resp1 = client.post("/api/run?target=KRAS+G12D&candidates=2", headers=headers)
    assert resp1.status_code == 200
    res1 = resp1.json()
    assert res1["status"] == "completed"
    assert res1["trial_status"]["runs_used"] == 1
    assert res1["trial_status"]["runs_remaining"] == 0
    assert res1["trial_status"]["is_locked"] is True

    # 3. Second Run -> MUST BE 403 FORBIDDEN
    resp2 = client.post("/api/run?target=EGFR+T790M&candidates=2", headers=headers)
    assert resp2.status_code == 403
    res2 = resp2.json()
    assert res2["error"] == "TRIAL_LIMIT_EXCEEDED"
    assert res2["runs_used"] == 1
    assert res2["runs_remaining"] == 0

    # 4. Exploit attempt: Clear cookies (fresh client), same fingerprint
    fresh_client = TestClient(serve_cockpit.app)
    resp3 = fresh_client.post("/api/run?target=Mpro&candidates=2", headers=headers)
    assert resp3.status_code == 403
    assert resp3.json()["error"] == "TRIAL_LIMIT_EXCEEDED"
