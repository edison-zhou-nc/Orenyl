"""Small resettable lazy initialization helper."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Generic, TypeVar, cast

_T = TypeVar("_T")
_UNSET = object()


class Lazy(Generic[_T]):
    """Thread-safe lazy initializer with explicit reset support."""

    def __init__(self, factory: Callable[[], _T]):
        self._factory = factory
        self._value: _T | object = _UNSET
        self._lock = threading.Lock()

    @property
    def value(self) -> _T:
        if self._value is _UNSET:
            with self._lock:
                if self._value is _UNSET:
                    self._value = self._factory()
        return self._value  # type: ignore[return-value]

    def reset(self) -> _T | None:
        with self._lock:
            previous = None if self._value is _UNSET else cast(_T, self._value)
            self._value = _UNSET
            return previous
