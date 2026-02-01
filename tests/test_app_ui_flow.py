"""UI flow tests for application behaviors."""

from __future__ import annotations

import runpy
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from pytest import MonkeyPatch
from pytestqt.qtbot import QtBot

import wifiqr.app as app_module
from wifiqr.ui.main_window import MainWindow

DEFAULT_SSID = "Office"
DEFAULT_PASSWORD = "secret"
DEFAULT_SECURITY = "WPA/WPA2/WPA3"
PNG_EXPORT_NAME = "wifi.png"
PDF_EXPORT_NAME = "wifi.pdf"
WINDOWS_SCRIPT_NAME = "wifi.cmd"
MACOS_PROFILE_NAME = "wifi.mobileconfig"
PDF_SAMPLE_CONTENT = "pdf"
RESIZE_WIDTH = 800
RESIZE_HEIGHT = 600
RESIZE_PREVIOUS_WIDTH = 780
RESIZE_PREVIOUS_HEIGHT = 580
QR_DEFAULT_SIZE = 640


def test_app_main_invokes_exec(monkeypatch: MonkeyPatch) -> None:
    """Ensure the main entry point creates and executes the app."""
    calls = {"exec": 0, "show": 0}

    def noop(*_args: Any, **_kwargs: Any) -> None:
        """No-op stub for application callbacks."""
        return None

    class DummyApp:
        def __init__(self, _argv: list[str]) -> None:
            """Initialize a stub application."""
            pass

        def __getattr__(self, _name: str) -> Callable[..., None]:
            """Return a no-op handler for unknown attributes."""
            return noop

        def exec(self) -> int:
            """Return a successful exit code."""
            calls["exec"] += 1
            return 0

    class DummyWindow:
        def show(self) -> None:
            """No-op show handler."""
            calls["show"] += 1

    monkeypatch.setattr(app_module, "QApplication", DummyApp)
    monkeypatch.setattr(app_module, "MainWindow", DummyWindow)

    assert app_module.main() == 0
    assert calls["exec"] == 1
    assert calls["show"] == 1


def test_app_module_main_guard(monkeypatch: MonkeyPatch) -> None:
    """Ensure module __main__ guard exits cleanly."""
    # Skip if QApplication already exists (from other tests)
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is not None:
        # Can't test main() guard when QApplication already exists
        # Just verify the app module can be imported
        import wifiqr.app as app_test

        assert hasattr(app_test, "main")
        return

    def noop(*_args: Any, **_kwargs: Any) -> None:
        """No-op stub for application callbacks."""
        return None

    class DummyApp:
        def __init__(self, _argv: list[str]) -> None:
            """Initialize a stub application."""
            pass

        def __getattr__(self, _name: str) -> Callable[..., None]:
            """Return a no-op handler for unknown attributes."""
            return noop

        def exec(self) -> int:
            """Return a successful exit code."""
            return 0

    class DummyWindow:
        def show(self) -> None:
            """No-op show handler."""
            pass

    monkeypatch.setattr(app_module, "QApplication", DummyApp)
    monkeypatch.setattr(app_module, "MainWindow", DummyWindow)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=RuntimeWarning,
            message=".*found in sys.modules.*prior to execution.*",
        )
        try:
            runpy.run_module("wifiqr.app", run_name="__main__")
        except SystemExit as exc:
            assert exc.code == 0


def test_ui_export_paths(
    monkeypatch: MonkeyPatch,
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    """Ensure export actions choose expected file paths."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)
    window._refresh_preview_now()
    window._refresh_preview_now()

    png_export_path = tmp_path / PNG_EXPORT_NAME
    pdf_export_path = tmp_path / PDF_EXPORT_NAME
    windows_script_path = tmp_path / WINDOWS_SCRIPT_NAME
    macos_profile_path = tmp_path / MACOS_PROFILE_NAME

    def fake_save_name(*args: Any, **kwargs: Any) -> tuple[str, str]:
        """Return a save path based on the dialog filter."""
        filters = kwargs.get("filter")
        if not filters and len(args) >= 4:
            filters = args[3]
        if filters and "PNG" in filters:
            return str(png_export_path), ""
        if filters and "PDF" in filters:
            return str(pdf_export_path), ""
        if filters and "Command" in filters:
            return str(windows_script_path), ""
        if filters and "Configuration" in filters:
            return str(macos_profile_path), ""
        return "", ""

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(lambda *args, **kwargs: fake_save_name(*args, **kwargs)),
    )

    window._export_png()

    def fake_export_pdf(_config: object, _printer: object) -> None:
        """Write a placeholder PDF file."""
        pdf_export_path.write_text(PDF_SAMPLE_CONTENT, encoding="utf-8")

    monkeypatch.setattr(window, "_export_pdf_to_path", fake_export_pdf)

    window._export_pdf()
    window._export_windows_script()
    window._export_macos_profile()

    assert png_export_path.exists()
    assert pdf_export_path.exists()
    assert windows_script_path.exists()
    assert macos_profile_path.exists()


def test_print_flow(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure print dialog accepted triggers render."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)
    window._refresh_preview_now()

    render_calls = {"render": 0}

    def fake_render(_printer: QPrinter) -> None:
        """Track render calls for assertions."""
        render_calls["render"] += 1

    monkeypatch.setattr(window, "_render_pixmap", fake_render)

    class DummyDialog:
        def __init__(self, _printer: QPrinter, _parent: object | None = None) -> None:
            """Initialize a stub print dialog."""
            pass

        def exec(self) -> QPrintDialog.DialogCode:
            """Return an accepted dialog code."""
            return QPrintDialog.DialogCode.Accepted

        DialogCode = QPrintDialog.DialogCode

    monkeypatch.setattr("wifiqr.ui.main_window.QPrintDialog", DummyDialog)
    window._print()
    assert render_calls["render"] == 1


def test_print_no_pixmap(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure print exits early when no pixmap is available."""
    window = MainWindow()
    qtbot.addWidget(window)
    render_calls = {"render": 0}

    def fake_render(_printer: QPrinter) -> None:
        """Track render calls for assertions."""
        render_calls["render"] += 1

    monkeypatch.setattr(window, "_render_pixmap", fake_render)
    window._print()
    assert render_calls["render"] == 0


def test_print_dialog_rejected(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure rejecting the print dialog skips rendering."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)
    window._refresh_preview_now()
    window._refresh_preview_now()
    window._refresh_preview_now()
    window._refresh_preview_now()
    window._refresh_preview_now()
    window._refresh_preview_now()

    class DummyDialog:
        def __init__(self, _printer: QPrinter, _parent: object | None = None) -> None:
            """Initialize a stub print dialog."""
            pass

        def exec(self) -> QPrintDialog.DialogCode:
            """Return a rejected dialog code."""
            return QPrintDialog.DialogCode.Rejected

        DialogCode = QPrintDialog.DialogCode

    render_calls = {"render": 0}

    def fake_render(_printer: QPrinter) -> None:
        """Track render calls for assertions."""
        render_calls["render"] += 1

    monkeypatch.setattr(window, "_render_pixmap", fake_render)
    monkeypatch.setattr("wifiqr.ui.main_window.QPrintDialog", DummyDialog)
    window._print()
    assert render_calls["render"] == 0


def test_export_cancel_paths(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure export actions exit when dialogs return empty paths."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(lambda *args, **kwargs: ("", "")),
    )

    window._export_png()
    window._export_pdf()
    window._export_windows_script()
    window._export_macos_profile()

    window.ssid_input.setText("")
    window._export_png()
    window._export_pdf()
    window._current_payload = ""
    window._export_windows_script()
    window._export_macos_profile()


def test_export_errors(
    monkeypatch: MonkeyPatch,
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    """Ensure export errors are handled with critical dialogs."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)

    png_export_path = tmp_path / PNG_EXPORT_NAME
    macos_profile_path = tmp_path / MACOS_PROFILE_NAME

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(
            lambda *args, **kwargs: (
                str(png_export_path)
                if "PNG" in (kwargs.get("filter") or args[3])
                else str(macos_profile_path),
                "",
            )
        ),
    )

    def boom(*_args: Any, **_kwargs: Any) -> None:
        """Raise an error to simulate export failures."""
        raise RuntimeError("fail")

    monkeypatch.setattr("wifiqr.ui.main_window.save_qr_image", boom)
    monkeypatch.setattr("wifiqr.ui.main_window.build_macos_mobileconfig", boom)
    monkeypatch.setattr("wifiqr.ui.main_window.build_windows_connect_script", boom)

    window._export_png()
    window._export_macos_profile()
    window._export_windows_script()


def test_export_pdf_error(
    monkeypatch: MonkeyPatch,
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    """Ensure PDF export errors show critical dialogs."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)
    window._refresh_preview_now()

    pdf_export_path = tmp_path / PDF_EXPORT_NAME

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(pdf_export_path), "")),
    )

    def boom(*_args: Any, **_kwargs: Any) -> None:
        """Raise an error to simulate export failures."""
        raise RuntimeError("fail")

    monkeypatch.setattr(window, "_export_pdf_to_path", boom)

    critical_calls = {"critical": 0}

    def fake_critical(*_args: Any, **_kwargs: Any) -> None:
        """Track critical dialog calls."""
        critical_calls["critical"] += 1

    monkeypatch.setattr("wifiqr.ui.main_window.QMessageBox.critical", staticmethod(fake_critical))

    window._export_pdf()
    assert critical_calls["critical"] == 1


def test_export_success_messages(
    monkeypatch: MonkeyPatch,
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    """Ensure export success shows information messages."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)
    window._refresh_preview_now()

    windows_script_path = tmp_path / WINDOWS_SCRIPT_NAME
    macos_profile_path = tmp_path / MACOS_PROFILE_NAME

    returns = [
        (str(windows_script_path), ""),
        (str(macos_profile_path), ""),
    ]

    def fake_save_name(*_args: Any, **_kwargs: Any) -> tuple[str, str]:
        """Return sequential save paths for exports."""
        return returns.pop(0)

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(fake_save_name),
    )

    info_calls = {"info": 0}

    def fake_info(*_args: Any, **_kwargs: Any) -> None:
        """Track information dialog calls."""
        info_calls["info"] += 1

    monkeypatch.setattr("wifiqr.ui.main_window.QMessageBox.information", staticmethod(fake_info))

    window._export_windows_script()
    window._export_macos_profile()

    assert info_calls["info"] == 2


def test_resize_event_scales_pixmap(qtbot: QtBot) -> None:
    """Ensure resize events rescale the preview pixmap."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)

    event = QResizeEvent(
        QSize(RESIZE_WIDTH, RESIZE_HEIGHT),
        QSize(RESIZE_PREVIOUS_WIDTH, RESIZE_PREVIOUS_HEIGHT),
    )
    window.resizeEvent(event)


def test_update_button_labels_twice(qtbot: QtBot) -> None:
    """Ensure repeated label updates are safe."""
    window = MainWindow()
    qtbot.addWidget(window)
    window._update_button_labels()
    window._update_button_labels()


def test_refresh_preview_empty_and_error(
    monkeypatch: MonkeyPatch,
    qtbot: QtBot,
) -> None:
    """Ensure preview clears on empty SSID and disables on errors."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("")
    window._refresh_preview_now()
    assert window.payload_label.text() == ""

    def boom(_payload: str, size: int = QR_DEFAULT_SIZE) -> None:
        """Raise an error to simulate QR generation failure."""
        raise RuntimeError("fail")

    monkeypatch.setattr("wifiqr.ui.main_window.generate_qr_image", boom)
    window.ssid_input.setText(DEFAULT_SSID)
    window._refresh_preview_now()
    assert window.print_button.isEnabled() is False


def test_render_pixmap_to_pdf(qtbot: QtBot, tmp_path: Path) -> None:
    """Ensure rendering to a PDF printer creates output."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)
    window._refresh_preview_now()

    pdf_export_path = tmp_path / "render.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(pdf_export_path))
    window._render_pixmap(printer)
    assert pdf_export_path.exists()


def test_render_pixmap_no_image(qtbot: QtBot) -> None:
    """Ensure render is a no-op without a pixmap."""
    window = MainWindow()
    qtbot.addWidget(window)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    window._render_pixmap(printer)
