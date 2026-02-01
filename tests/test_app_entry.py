"""Tests for application entry point."""

from __future__ import annotations

import runpy
import sys
from types import ModuleType

import pytest
from _pytest.monkeypatch import MonkeyPatch

from wifiqr import app


def test_main_runs_app(monkeypatch: MonkeyPatch) -> None:
    """Ensure main wires up QApplication and MainWindow."""
    calls: dict[str, object] = {}

    class FakeApp:
        def __init__(self, argv: list[str]) -> None:
            calls["argv"] = argv

        def setApplicationName(self, name: str) -> None:  # noqa: N802
            calls["app_name"] = name

        def setOrganizationName(self, name: str) -> None:  # noqa: N802
            calls["org_name"] = name

        def exec(self) -> int:
            return 42

    class FakeWindow:
        def show(self) -> None:
            calls["shown"] = True

    monkeypatch.setattr(app, "QApplication", FakeApp)
    monkeypatch.setattr(app, "MainWindow", FakeWindow)

    result = app.main()

    assert result == 42
    assert calls["argv"] == sys.argv
    assert calls["app_name"] == "WifiQR"
    assert calls["org_name"] == "WifiQR"
    assert calls["shown"] is True


def test_module_main_guard_executes(monkeypatch: MonkeyPatch) -> None:
    """Ensure __main__ guard executes and exits with app code."""

    class FakeApp:
        def __init__(self, argv: list[str]) -> None:  # noqa: ARG002
            pass

        def setApplicationName(self, name: str) -> None:  # noqa: ARG002,N802
            pass

        def setOrganizationName(self, name: str) -> None:  # noqa: ARG002,N802
            pass

        def exec(self) -> int:
            return 7

    class FakeWindow:
        def show(self) -> None:
            pass

    qtwidgets = ModuleType("PySide6.QtWidgets")
    setattr(qtwidgets, "QApplication", FakeApp)
    monkeypatch.setitem(sys.modules, "PySide6.QtWidgets", qtwidgets)

    import wifiqr.ui.main_window as main_window

    monkeypatch.setattr(main_window, "MainWindow", FakeWindow)

    sys.modules.pop("wifiqr.app", None)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("wifiqr.app", run_name="__main__")

    assert excinfo.value.code == 7
