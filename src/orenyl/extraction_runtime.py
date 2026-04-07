"""Runtime wrapper for extraction rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from .extraction_rule import ExtractionFact, ExtractionRule


@dataclass
class NullExtractionRuntime:
    def extract_facts(self, event: dict) -> list[ExtractionFact]:
        return []


@dataclass
class RuleBasedExtractionRuntime:
    rules: list[ExtractionRule] = field(default_factory=list)

    def extract_facts(self, event: dict) -> list[ExtractionFact]:
        extracted: list[ExtractionFact] = []
        for rule in self.rules:
            extracted.extend(rule.extract(event))
        return extracted
