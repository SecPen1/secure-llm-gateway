import hashlib

import pytest

import gateway.audit_log as audit_log_module
import gateway.auth as auth_module

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
