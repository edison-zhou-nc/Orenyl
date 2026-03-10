"""Embedding storage helpers."""

from __future__ import annotations

import json


def encode_vector(vector: list[float]) -> str:
    return json.dumps([float(v) for v in vector])


def decode_vector(raw: str) -> list[float]:
    values = json.loads(raw or "[]")
    return [float(v) for v in values]
