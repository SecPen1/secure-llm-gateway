from fastapi.testclient import TestClient

from gateway.main import app

client = TestClient(app)

TEST_CLIENT_ID = "demo-client"


def test_valid_request_is_accepted(auth_headers):
    response = client.post(
        "/v1/chat",
        json={
            "client_id": TEST_CLIENT_ID,
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_missing_required_field_is_rejected(auth_headers):
    response = client.post("/v1/chat", json={"messages": []}, headers=auth_headers)
    assert response.status_code == 422


def test_empty_messages_list_is_rejected(auth_headers):
    response = client.post(
        "/v1/chat",
        json={"client_id": TEST_CLIENT_ID, "messages": []},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_oversized_content_is_rejected(auth_headers):
    response = client.post(
        "/v1/chat",
        json={
            "client_id": TEST_CLIENT_ID,
            "messages": [{"role": "user", "content": "x" * 5000}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_invalid_role_is_rejected(auth_headers):
    response = client.post(
        "/v1/chat",
        json={
            "client_id": TEST_CLIENT_ID,
            "messages": [{"role": "root", "content": "hello"}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
