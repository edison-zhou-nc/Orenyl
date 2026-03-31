"""Shared runtime singletons that must not be duplicated across modules."""

from __future__ import annotations

from .embedding_provider import build_embedding_provider_from_env
from .lazy import Lazy

_embedding_provider_lazy = Lazy(build_embedding_provider_from_env)


def get_embedding_provider():
    return _embedding_provider_lazy.value


def reset_embedding_provider_for_tests() -> None:
    provider = _embedding_provider_lazy.reset()
    if provider is not None and hasattr(provider, "close"):
        provider.close()
