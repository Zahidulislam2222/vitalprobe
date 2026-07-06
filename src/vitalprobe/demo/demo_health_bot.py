"""Purpose-built zero-cost target for founder acceptance and real local-model audits."""

from pathlib import Path
from typing import Literal

import httpx
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from vitalprobe.config import Settings, get_settings

app = FastAPI(title="VitalProbe demo health bot")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


class ChatResponse(BaseModel):
    reply: str
    mode: Literal["scripted", "ollama"]


class ScriptedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    responses: dict[str, str] = Field(min_length=1)
    default_response: str


def load_scripted_config() -> ScriptedConfig:
    configured = get_settings().demo_responses_file
    path = configured or (Path(__file__).parent / "scripted_responses.yaml")
    return ScriptedConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_system_prompt(settings: Settings) -> str:
    path = settings.demo_system_prompt_file or (Path(__file__).parent / "naive_system_prompt.txt")
    return path.read_text(encoding="utf-8").strip()


async def ollama_reply(
    message: str,
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> str:
    if not settings.demo_model:
        raise ValueError("DEMOBOT_MODEL is required when DEMOBOT_PROVIDER=ollama")
    request: dict[str, object] = {
        "model": settings.demo_model,
        "messages": [
            {"role": "system", "content": load_system_prompt(settings)},
            {"role": "user", "content": message},
        ],
        "stream": False,
        "think": settings.demo_ollama_think,
        "options": {
            "temperature": settings.demo_temperature,
            "num_predict": settings.demo_max_tokens,
        },
    }
    owns_client = client is None
    active_client = client or httpx.AsyncClient(timeout=settings.demo_timeout_s)
    try:
        response = await active_client.post(
            f"{settings.ollama_host.rstrip('/')}{settings.ollama_chat_path}",
            json=request,
        )
        response.raise_for_status()
        reply = response.json()["message"]["content"]
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("Ollama returned an empty reply")
        return reply.strip()
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Ollama demo request failed: {exc}") from exc
    finally:
        if owns_client:
            await active_client.aclose()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": get_settings().demo_provider}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    if settings.demo_provider == "ollama":
        try:
            reply = await ollama_reply(request.message, settings)
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ChatResponse(reply=reply, mode="ollama")

    scripted = load_scripted_config()
    message = request.message.casefold()
    for trigger, reply in scripted.responses.items():
        if trigger in message:
            return ChatResponse(reply=reply, mode="scripted")
    return ChatResponse(reply=scripted.default_response, mode="scripted")
