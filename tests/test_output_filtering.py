from fastapi.testclient import TestClient

from gateway.main import app

client = TestClient(app)

TEST_CLIENT_ID = "demo-client"


def _post(content: str, headers):
    return client.post(
        "/v1/chat",
        json={
            "client_id": TEST_CLIENT_ID,
            "messages": [{"role": "user", "content": content}],
        },
        headers=headers,
    )


def test_response_with_credit_card_is_redacted(auth_headers):
    response = _post("My card number is 4111-1111-1111-1111, please remember it.", auth_headers)
    body = response.json()
    assert response.status_code == 200
    assert "4111-1111-1111-1111" not in body["response"]
    assert "credit_card" in body["redactions"]


def test_response_with_ssn_is_redacted(auth_headers):
    response = _post("My SSN is 123-45-6789.", auth_headers)
    body = response.json()
    assert "123-45-6789" not in body["response"]
    assert "ssn" in body["redactions"]


def test_response_with_aws_key_is_redacted(auth_headers):
    response = _post("Here is a key: AKIAABCDEFGHIJKLMNOP", auth_headers)
    body = response.json()
    assert "AKIAABCDEFGHIJKLMNOP" not in body["response"]
    assert "aws_access_key" in body["redactions"]


def test_response_with_generic_api_key_is_redacted(auth_headers):
    response = _post("Use this token: sk-abcdefghijklmnopqrstuvwxyz1234", auth_headers)
    body = response.json()
    assert "sk-abcdefghijklmnopqrstuvwxyz1234" not in body["response"]
    assert "generic_api_key" in body["redactions"]


def test_benign_response_has_no_redactions(auth_headers):
    response = _post("What's the weather like today?", auth_headers)
    body = response.json()
    assert response.status_code == 200
    assert body["redactions"] == []
