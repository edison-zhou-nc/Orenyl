"""Shared derivation rule base types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DerivationRule(ABC):
    """Base class for all derivation rules."""

    rule_id: str = ""
    output_key: str = ""

    @abstractmethod
    def derive(self, events: list[dict]) -> Any:
        """Given a list of active events, produce a fact value."""
        ...

    @abstractmethod
    def relevant_event_types(self) -> list[str]:
        """Which event types does this rule care about?"""
        ...
