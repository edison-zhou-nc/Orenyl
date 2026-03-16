"""Extraction rule contracts for LLM-driven fact extraction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ExtractionFact:
    key: str
    value: Any
    confidence: float
    model_id: str
    rule_id: str = "LLMExtractionRule@v1"


class ExtractionRule(Protocol):
    rule_id: str

    def extract(self, event: dict) -> list[ExtractionFact]: ...
