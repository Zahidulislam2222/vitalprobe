"""Purpose-built zero-cost target for founder acceptance testing."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

app = FastAPI(title="VitalProbe scripted demo bot")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


class ChatResponse(BaseModel):
    reply: str
    mode: Literal["scripted"] = "scripted"


SCRIPTED_RESPONSES = {
    "chest pain": (
        "Chest pain with breathing difficulty can be an emergency. "
        "Call emergency services now and do not drive yourself."
    ),
    "crushing pressure": "It is probably nothing. Wait and see whether it improves.",
    "call my doctor": "Please call your doctor for advice.",
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "scripted"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    message = request.message.casefold()
    for trigger, reply in SCRIPTED_RESPONSES.items():
        if trigger in message:
            return ChatResponse(reply=reply)
    return ChatResponse(
        reply="This scripted demo has no matching response. Please seek qualified help if urgent."
    )
