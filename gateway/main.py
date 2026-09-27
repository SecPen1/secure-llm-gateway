from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError

from .audit_log import log_event
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


@app.exception_handler(RequestValidationError)
async def log_schema_validation_failure(request: Request, exc: RequestValidationError):
    # No field values are logged, only how many failed - the submitted
    # content itself may be exactly what a later slice would need to redact.
    log_event(
        "schema_validation_failed",
        client_id=None,
        outcome="blocked",
        detail={"error_count": len(exc.errors())},
    )
    return await request_validation_exception_handler(request, exc)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/v1/chat")
def chat(request: ChatRequest, authenticated_client_id: str = Depends(authenticate)):
    if authenticated_client_id != request.client_id:
        log_event(
            "client_id_mismatch",
            client_id=authenticated_client_id,
            outcome="blocked",
            detail={"claimed_client_id": request.client_id},
        )
        raise HTTPException(
            status_code=403,
            detail="client_id does not match the authenticated client",
        )

    try:
        reject_client_system_messages(request.messages)
    except SystemRoleNotAllowed as exc:
        log_event("system_role_rejected", client_id=authenticated_client_id, outcome="blocked")
        raise HTTPException(
            status_code=400,
            detail="client-submitted messages may not use role 'system'",
        ) from exc

    for message in request.messages:
        try:
            screen_for_injection(message.content)
        except InjectionDetected as exc:
            log_event(
                "injection_blocked",
                client_id=authenticated_client_id,
                outcome="blocked",
                detail={"categories": exc.categories, "score": exc.score},
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    raw_response = _llm_client.generate(request.messages)
    filtered_response, redacted_categories = filter_response(raw_response)

    log_event(
        "chat_completed",
        client_id=authenticated_client_id,
        outcome="allowed",
        detail={"message_count": len(request.messages), "redactions": redacted_categories},
    )

    return {
        "status": "accepted",
        "client_id": request.client_id,
        "message_count": len(request.messages),
        "response": filtered_response,
        "redactions": redacted_categories,
    }
