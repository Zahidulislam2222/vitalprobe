"""Purpose-built zero-cost target for founder acceptance testing."""

from pathlib import Path
from typing import Literal

import yaml
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from vitalprobe.config import get_settings

app = FastAPI(title="VitalProbe scripted demo bot")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


class ChatResponse(BaseModel):
    reply: str
    mode: Literal["scripted"] = "scripted"


class ScriptedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    responses: dict[str, str] = Field(min_length=1)
    default_response: str


def load_scripted_config() -> ScriptedConfig:
    configured = get_settings().demo_responses_file
    path = configured or (Path(__file__).parent / "scripted_responses.yaml")
    return ScriptedConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "scripted"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    scripted = load_scripted_config()
    message = request.message.casefold()
    for trigger, reply in scripted.responses.items():
        if trigger in message:
            return ChatResponse(reply=reply)
    return ChatResponse(reply=scripted.default_response)
