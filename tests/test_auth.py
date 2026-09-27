from fastapi.testclient import TestClient

from gateway.main import app

client = TestClient(app)

TEST_CLIENT_ID = "demo-client"


def _payload(client_id: str = TEST_CLIENT_ID) -> dict:
    return {
        "client_id": client_id,
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_request_without_auth_header_is_rejected(auth_headers):
    response = client.post("/v1/chat", json=_payload())
    assert response.status_code == 401


def test_request_with_invalid_key_is_rejected(auth_headers):
    response = client.post(
        "/v1/chat",
        json=_payload(),
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


def test_request_with_valid_key_is_accepted(auth_headers):
    response = client.post("/v1/chat", json=_payload(), headers=auth_headers)
    assert response.status_code == 200


def test_client_id_spoofing_is_rejected(auth_headers):
    response = client.post(
        "/v1/chat",
        json=_payload(client_id="someone-else"),
        headers=auth_headers,
    )
    assert response.status_code == 403
