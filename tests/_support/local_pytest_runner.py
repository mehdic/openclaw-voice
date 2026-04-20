from __future__ import annotations

import importlib.util
import inspect
import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import pytest


@dataclass
class _FixtureResult:
    value: Any
    teardown: Callable[[], None] | None


class _FixtureRegistry:
    def __init__(self) -> None:
        self._fixtures: dict[str, Callable[..., Any]] = {}
        self._autouse: list[str] = []

    def register_module(self, module: ModuleType) -> None:
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and getattr(obj, "_pytest_fixture", False):
                self._fixtures[name] = obj
                if getattr(obj, "_pytest_autouse", False):
                    self._autouse.append(name)

    def resolve(
        self,
        name: str,
        cache: dict[str, _FixtureResult],
        stack: list[Callable[[], None]],
    ) -> Any:
        if name in cache:
            return cache[name].value

        if name == "tmp_path":
            temp_dir = tempfile.TemporaryDirectory()
            value = Path(temp_dir.name)
            result = _FixtureResult(value=value, teardown=temp_dir.cleanup)
            cache[name] = result
            stack.append(temp_dir.cleanup)
            return value

        if name == "monkeypatch":
            mp = pytest.MonkeyPatch()
            result = _FixtureResult(value=mp, teardown=mp.undo)
            cache[name] = result
            stack.append(mp.undo)
            return mp

        fixture_func = self._fixtures.get(name)
        if fixture_func is None:
            raise KeyError(f"Unknown fixture: {name}")

        kwargs = {
            dep_name: self.resolve(dep_name, cache, stack)
            for dep_name in inspect.signature(fixture_func).parameters
        }

        teardown = None
        if inspect.isgeneratorfunction(fixture_func):
            generator = fixture_func(**kwargs)
            value = next(generator)

            def teardown() -> None:
                try:
                    next(generator)
                except StopIteration:
                    return
                raise RuntimeError(f"Fixture {name} yielded more than once")

        else:
            value = fixture_func(**kwargs)

        result = _FixtureResult(value=value, teardown=teardown)
        cache[name] = result
        if teardown is not None:
            stack.append(teardown)
        return value


def _load_module(module_name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _iter_test_functions(module: ModuleType):
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and name.startswith("test_"):
            yield name, obj


def main() -> int:
    root = Path.cwd()
    tests_dir = root / "tests"
    registry = _FixtureRegistry()

    conftest_path = tests_dir / "conftest.py"
    if conftest_path.exists():
        registry.register_module(_load_module("tests.conftest", conftest_path))

    test_files = sorted(path for path in tests_dir.glob("test_*.py") if path.is_file())

    passed = 0
    failed = 0

    for test_file in test_files:
        module_name = f"tests.{test_file.stem}"
        module = _load_module(module_name, test_file)
        registry.register_module(module)

        for test_name, test_func in _iter_test_functions(module):
            cache: dict[str, _FixtureResult] = {}
            teardowns: list[Callable[[], None]] = []

            try:
                for fixture_name in registry._autouse:
                    registry.resolve(fixture_name, cache, teardowns)

                kwargs = {
                    name: registry.resolve(name, cache, teardowns)
                    for name in inspect.signature(test_func).parameters
                }
                test_func(**kwargs)
            except Exception:
                failed += 1
                print(f"FAILED {module_name}::{test_name}")
                traceback.print_exc()
            else:
                passed += 1
                print(f"PASSED {module_name}::{test_name}")
            finally:
                while teardowns:
                    teardown = teardowns.pop()
                    teardown()

    total = passed + failed
    print(f"{total} tests collected")
    print(f"{passed} passed")
    print(f"{failed} failed")
    return 1 if failed else 0
