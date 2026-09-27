import hashlib

import pytest

import gateway.audit_log as audit_log_module
import gateway.auth as auth_module
import gateway.rate_limiter as rate_limiter_module

TEST_API_KEY = "test-demo-key-do-not-use"
TEST_CLIENT_ID = "demo-client"


@pytest.fixture
def auth_headers(monkeypatch):
    key_hash = hashlib.sha256(TEST_API_KEY.encode("utf-8")).hexdigest()
    monkeypatch.setattr(auth_module, "_CLIENTS", {TEST_CLIENT_ID: {"key_hash": key_hash}})
    return {"Authorization": f"Bearer {TEST_API_KEY}"}


@pytest.fixture(autouse=True)
def audit_log_path(monkeypatch, tmp_path):
    # Applied to every test, not just audit-log tests: without this, running
    # the suite would append real entries to logs/audit.log on disk.
    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit_log_module, "_LOG_PATH", log_path)
    monkeypatch.setattr(audit_log_module, "_last_hash", audit_log_module._GENESIS_HASH)
    return log_path


@pytest.fixture(autouse=True)
def reset_rate_limiter_state(monkeypatch):
    # Applied to every test: without this, request/cost counters would
    # accumulate across unrelated tests that reuse the same demo client_id.
    monkeypatch.setattr(rate_limiter_module, "_buckets", {})
    monkeypatch.setattr(rate_limiter_module, "_cost_usage", {})


@pytest.fixture
def fake_clock(monkeypatch):
    # Lets rate-limit tests advance time deterministically instead of
    # sleeping for real. current[0] += N moves the clock forward N seconds.
    current = [1_000_000.0]
    monkeypatch.setattr(rate_limiter_module, "_clock", lambda: current[0])
    return current
