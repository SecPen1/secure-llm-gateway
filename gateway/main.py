from fastapi import Depends, FastAPI, HTTPException

from .auth import authenticate
from .injection_defense import (
    InjectionDetected,
    SystemRoleNotAllowed,
    reject_client_system_messages,
    screen_for_injection,
)
from .llm_client import get_llm_client
from .output_filter import filter_response
from .schemas import ChatRequest

app = FastAPI(title="Secure LLM Gateway", version="0.1.0")
_llm_client = get_llm_client()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/chat")
def chat(request: ChatRequest, authenticated_client_id: str = Depends(authenticate)):
    if authenticated_client_id != request.client_id:
        raise HTTPException(
            status_code=403,
            detail="client_id does not match the authenticated client",
        )

    try:
        reject_client_system_messages(request.messages)
    except SystemRoleNotAllowed as exc:
        raise HTTPException(
            status_code=400,
            detail="client-submitted messages may not use role 'system'",
        ) from exc

    for message in request.messages:
        try:
            screen_for_injection(message.content)
        except InjectionDetected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    raw_response = _llm_client.generate(request.messages)
    filtered_response, redacted_categories = filter_response(raw_response)

    return {
        "status": "accepted",
        "client_id": request.client_id,
        "message_count": len(request.messages),
        "response": filtered_response,
        "redactions": redacted_categories,
    }
