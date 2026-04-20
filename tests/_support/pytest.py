from __future__ import annotations

import os
from typing import Any, Callable


class MonkeyPatch:
    def __init__(self) -> None:
        self._undo: list[Callable[[], None]] = []

    def setattr(self, target: Any, name: str, value: Any) -> None:
        original = getattr(target, name)
        setattr(target, name, value)
        self._undo.append(lambda: setattr(target, name, original))

    def setenv(self, name: str, value: str) -> None:
        original = os.environ.get(name)
        os.environ[name] = value

        def undo() -> None:
            if original is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = original

        self._undo.append(undo)

    def delenv(self, name: str, raising: bool = True) -> None:
        if name not in os.environ:
            if raising:
                raise KeyError(name)
            return

        original = os.environ.pop(name)
        self._undo.append(lambda: os.environ.__setitem__(name, original))

    def undo(self) -> None:
        while self._undo:
            undo = self._undo.pop()
            undo()


def fixture(func: Callable[..., Any] | None = None, *, autouse: bool = False):
    def decorator(inner: Callable[..., Any]) -> Callable[..., Any]:
        inner._pytest_fixture = True  # type: ignore[attr-defined]
        inner._pytest_autouse = autouse  # type: ignore[attr-defined]
        return inner

    if func is None:
        return decorator
    return decorator(func)
