from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

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
from .rate_limiter import RateLimitExceeded, check_cost_budget, check_rate_limit, estimate_cost
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

    estimated_cost = estimate_cost(request.messages)
    try:
        check_rate_limit(authenticated_client_id)
        check_cost_budget(authenticated_client_id, estimated_cost)
    except RateLimitExceeded as exc:
        log_event(
            "rate_limited",
            client_id=authenticated_client_id,
            outcome="blocked",
            detail={"reason": exc.reason, "retry_after_seconds": round(exc.retry_after, 1)},
        )
        raise HTTPException(
            status_code=429,
            detail=f"rate limit exceeded ({exc.reason})",
            headers={"Retry-After": str(max(1, round(exc.retry_after)))},
        ) from exc

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
        detail={
            "message_count": len(request.messages),
            "estimated_cost": estimated_cost,
            "redactions": redacted_categories,
        },
    )

    return {
        "status": "accepted",
        "client_id": request.client_id,
        "message_count": len(request.messages),
        "response": filtered_response,
        "redactions": redacted_categories,
    }


# Mounted last, deliberately: FastAPI/Starlette match routes in registration
# order, so /healthz and /v1/chat above are matched first. This local-only
# demo page is a plain static file - no build step, no framework - talking to
# the API above exactly like any other client would.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
