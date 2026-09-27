from fastapi import Depends, FastAPI, HTTPException

from .auth import authenticate
from .schemas import ChatRequest
from .validation import InjectionDetected, screen_for_injection

app = FastAPI(title="Secure LLM Gateway", version="0.1.0")


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

    for message in request.messages:
        try:
            screen_for_injection(message.content)
        except InjectionDetected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "accepted",
        "client_id": request.client_id,
        "message_count": len(request.messages),
    }
