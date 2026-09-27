from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class Message(BaseModel):
    role: Role
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=128)
    messages: list[Message] = Field(..., min_length=1, max_length=50)
