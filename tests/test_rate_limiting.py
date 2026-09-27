from fastapi.testclient import TestClient

import gateway.rate_limiter as rate_limiter_module
from gateway.main import app

client = TestClient(app)

TEST_CLIENT_ID = "demo-client"


def _chat(content: str = "hello", headers=None):
    return client.post(
        "/v1/chat",
        json={"client_id": TEST_CLIENT_ID, "messages": [{"role": "user", "content": content}]},
        headers=headers,
    )


def test_requests_within_capacity_are_allowed(auth_headers, monkeypatch, fake_clock):
    monkeypatch.setattr(rate_limiter_module, "RATE_CAPACITY", 3)
    for _ in range(3):
        assert _chat(headers=auth_headers).status_code == 200


def test_request_beyond_capacity_is_rate_limited(auth_headers, monkeypatch, fake_clock):
    monkeypatch.setattr(rate_limiter_module, "RATE_CAPACITY", 2)
    assert _chat(headers=auth_headers).status_code == 200
    assert _chat(headers=auth_headers).status_code == 200

    response = _chat(headers=auth_headers)
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert response.json()["detail"] == "rate limit exceeded (request_rate)"


def test_rate_limit_recovers_after_refill_window(auth_headers, monkeypatch, fake_clock):
    monkeypatch.setattr(rate_limiter_module, "RATE_CAPACITY", 1)
    monkeypatch.setattr(rate_limiter_module, "RATE_REFILL_PER_SECOND", 1.0)

    assert _chat(headers=auth_headers).status_code == 200
    assert _chat(headers=auth_headers).status_code == 429

    fake_clock[0] += 2  # enough time for one token to refill

    assert _chat(headers=auth_headers).status_code == 200


def test_cost_budget_exceeded_is_blocked(auth_headers, monkeypatch, fake_clock):
    monkeypatch.setattr(rate_limiter_module, "RATE_CAPACITY", 100)  # isolate cost budget from rate limit
    monkeypatch.setattr(rate_limiter_module, "DAILY_COST_BUDGET", 10)

    assert _chat("short", headers=auth_headers).status_code == 200  # 5 chars, within budget

    response = _chat("this message is long enough to exceed budget", headers=auth_headers)
    assert response.status_code == 429
    assert response.json()["detail"] == "rate limit exceeded (cost_budget)"


def test_cost_budget_resets_after_window(auth_headers, monkeypatch, fake_clock):
    monkeypatch.setattr(rate_limiter_module, "RATE_CAPACITY", 100)
    monkeypatch.setattr(rate_limiter_module, "DAILY_COST_BUDGET", 10)
    monkeypatch.setattr(rate_limiter_module, "COST_WINDOW_SECONDS", 60)

    assert _chat("0123456789", headers=auth_headers).status_code == 200  # exactly at budget
    assert _chat("x", headers=auth_headers).status_code == 429

    fake_clock[0] += 61  # past the window

    assert _chat("x", headers=auth_headers).status_code == 200


def test_unauthenticated_requests_are_not_rate_limited_as_a_client(fake_clock):
    # No auth header means no authenticated client_id is ever reached, so
    # this exercises the auth-failure path, not the rate limiter.
    response = _chat(headers=None)
    assert response.status_code == 401
