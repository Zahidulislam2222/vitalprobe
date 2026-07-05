"""Shared semantic judge contracts and rubric loading."""

from pathlib import Path
from typing import Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field

from vitalprobe.schema import JudgeResult, TestCase


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    description: str
    criteria: list[str] = Field(min_length=1)
    scale: str = "0-5"
    pass_at: float = 4
    warn_at: float = 3


class JudgeBackend(Protocol):
    async def score(
        self, rubric: Rubric, case: TestCase, response_text: str
    ) -> JudgeResult: ...


class JudgeError(Exception):
    """A judge request or response failed."""


def load_rubric(rubric_id: str) -> Rubric:
    path = Path(__file__).parent / "rubrics" / f"{rubric_id}.yaml"
    if not path.is_file():
        raise ValueError(f"unknown rubric: {rubric_id}")
    return Rubric.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
