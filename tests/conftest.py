import hashlib

import pytest

import gateway.auth as auth_module

TEST_API_KEY = "test-demo-key-do-not-use"
TEST_CLIENT_ID = "demo-client"


@pytest.fixture
def auth_headers(monkeypatch):
    key_hash = hashlib.sha256(TEST_API_KEY.encode("utf-8")).hexdigest()
    monkeypatch.setattr(auth_module, "_CLIENTS", {TEST_CLIENT_ID: {"key_hash": key_hash}})
    return {"Authorization": f"Bearer {TEST_API_KEY}"}
