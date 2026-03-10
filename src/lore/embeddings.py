"""Embedding storage helpers."""

from __future__ import annotations

import json
import math


def encode_vector(vector: list[float]) -> str:
    return json.dumps([float(v) for v in vector])


def decode_vector(raw: str) -> list[float]:
    values = json.loads(raw or "[]")
    return [float(v) for v in values]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a <= 0.0 or mag_b <= 0.0:
        return 0.0
    return dot / (mag_a * mag_b)
