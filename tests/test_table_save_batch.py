"""Table, save, and batch export tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QComboBox, QWidget
from pytest import MonkeyPatch
from pytestqt.qtbot import QtBot

from wifiqr.ui.main_window import MainWindow

DEFAULT_LOCATION = "HQ"
DEFAULT_SSID = "Office"
DEFAULT_PASSWORD = "secret"
DEFAULT_SECURITY = "WPA/WPA2/WPA3"
EXPORT_DIRECTORY_NAME = "out"
EXPORT_PNG_NAME = "Office.png"
EXPORT_PDF_NAME = "Office.pdf"
WINDOWS_BATCH_NAME = "wifi-batch.cmd"
MACOS_BATCH_NAME = "wifi-batch.mobileconfig"
SINGLE_PNG_NAME = "one.png"
SINGLE_PDF_NAME = "one.pdf"
SINGLE_WINDOWS_SCRIPT_NAME = "one.cmd"
SINGLE_MACOS_PROFILE_NAME = "one.mobileconfig"


def _populate(window: MainWindow) -> None:
    """Populate the form with a default Wi-Fi configuration."""
    window.location_input.setText(DEFAULT_LOCATION)
    window.ssid_input.setText(DEFAULT_SSID)
    window.password_input.setText(DEFAULT_PASSWORD)
    window.security_input.setCurrentText(DEFAULT_SECURITY)
    window.hidden_input.setChecked(True)


def test_add_and_row_config(qtbot: QtBot) -> None:
    """Ensure table rows are created and removed correctly."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)

    window._add_to_table()
    assert window.network_table.rowCount() == 1

    config = window._row_to_config(0)
    assert config is not None
    assert config.location == DEFAULT_LOCATION
    assert config.ssid == DEFAULT_SSID

    window.network_table.selectRow(0)
    window._remove_selected()
    assert window.network_table.rowCount() == 0


def test_password_toggle_and_edit(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure password toggling and edits update row data."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    window._toggle_password_visibility(0)
    window._toggle_password_visibility(0)

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QInputDialog.getText",
        staticmethod(lambda *args, **kwargs: ("editpass", True)),
    )
    window._view_password(0)
    item = window.network_table.item(0, 2)
    assert item is not None
    assert item.data(Qt.ItemDataRole.UserRole) == "editpass"


def test_edit_ssid(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure SSID edits update the table row."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QInputDialog.getText",
        staticmethod(lambda *args, **kwargs: ("NewSSID", True)),
    )
    window._edit_ssid(0)
    ssid_item = window.network_table.item(0, 1)
    assert ssid_item is not None
    assert ssid_item.text() == "NewSSID"


def test_security_combo_change(qtbot: QtBot) -> None:
    """Ensure security changes update the row value."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    combo = window.network_table.cellWidget(0, 3)
    assert isinstance(combo, QComboBox)
    combo.setCurrentText("WEP")
    config = window._row_to_config(0)
    assert config is not None
    assert config.security == "WEP"


def test_search_filter(qtbot: QtBot) -> None:
    """Ensure search filtering hides and selects rows."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    window.search_input.setText(DEFAULT_LOCATION.lower())
    window._apply_search_filter()
    assert window.network_table.isRowHidden(0) is False

    window.search_input.setText("nope")
    window._apply_search_filter()
    assert window.network_table.isRowHidden(0) is True

    window.search_input.setText("")
    window._apply_search_filter()
    assert window.network_table.isRowHidden(0) is False

    window.search_input.setText(DEFAULT_SSID.lower())
    window._apply_search_filter()
    window._find_next()
    window._find_previous()

    window.search_input.setText("")
    window._apply_search_filter()
    window._find_next()
    window._find_previous()


def test_sort_toggle(qtbot: QtBot) -> None:
    """Ensure sort order toggles per column click."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()
    window._handle_sort(0)
    window._handle_sort(1)
    window._handle_sort(2)


def test_table_context_menu(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure context menu actions are wired for SSID and password."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    monkeypatch.setattr("wifiqr.ui.main_window.QMenu.exec", lambda *args, **kwargs: None)

    ssid_item = window.network_table.item(0, 1)
    assert ssid_item is not None
    pos = window.network_table.visualItemRect(ssid_item).center()
    window._table_context_menu(pos)

    pwd_item = window.network_table.item(0, 2)
    assert pwd_item is not None
    pos = window.network_table.visualItemRect(pwd_item).center()
    window._table_context_menu(pos)

    window._table_context_menu(window.network_table.rect().bottomRight())


def test_save_load(tmp_path: Path, monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure save and load round-trip table data."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    save_path = tmp_path / "networks.json"
    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(save_path), "")),
    )
    window._save_as()
    assert save_path.exists()

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getOpenFileName",
        staticmethod(lambda *args, **kwargs: (str(save_path), "")),
    )
    window._load()
    assert window.location_input.text() == DEFAULT_LOCATION


def test_batch_export(tmp_path: Path, monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure batch export saves selected entries to disk."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    export_dir = tmp_path / EXPORT_DIRECTORY_NAME
    export_dir.mkdir()

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getExistingDirectory",
        staticmethod(lambda *args, **kwargs: str(export_dir)),
    )
    monkeypatch.setattr(
        "wifiqr.ui.main_window.QInputDialog.getItem",
        staticmethod(lambda *args, **kwargs: ("PNG", True)),
    )
    window._batch_export()
    assert (export_dir / EXPORT_PNG_NAME).exists()


def test_batch_export_paths(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    qtbot: QtBot,
) -> None:
    """Ensure batch export writes each output type."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    export_dir = tmp_path / EXPORT_DIRECTORY_NAME
    export_dir.mkdir()

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getExistingDirectory",
        staticmethod(lambda *args, **kwargs: str(export_dir)),
    )

    export_types = ["PNG", "PDF", "Windows Script", "macOS Profile"]

    def fake_get_item(*_args: Any, **_kwargs: Any) -> tuple[str, bool]:
        """Return the next export type for batch export tests."""
        return export_types.pop(0), True

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QInputDialog.getItem",
        staticmethod(fake_get_item),
    )

    window._batch_export()
    window._batch_export()
    window._batch_export()
    window._batch_export()

    assert (export_dir / EXPORT_PNG_NAME).exists()
    assert (export_dir / EXPORT_PDF_NAME).exists()
    assert (export_dir / WINDOWS_BATCH_NAME).exists()
    assert (export_dir / MACOS_BATCH_NAME).exists()


def test_batch_export_cancel_paths(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure batch export cancels cleanly on dialog dismissal."""
    window = MainWindow()
    qtbot.addWidget(window)

    window._batch_export()

    _populate(window)

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QInputDialog.getItem",
        staticmethod(lambda *args, **kwargs: ("PNG", False)),
    )
    window._batch_export()

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QInputDialog.getItem",
        staticmethod(lambda *args, **kwargs: ("PNG", True)),
    )
    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getExistingDirectory",
        staticmethod(lambda *args, **kwargs: ""),
    )
    window._batch_export()


def test_export_helpers(tmp_path: Path, qtbot: QtBot) -> None:
    """Ensure export helpers persist each output format."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    config = window._config

    png_path = tmp_path / SINGLE_PNG_NAME
    window._export_png_to_path(config, str(png_path))
    assert png_path.exists()

    pdf_path = tmp_path / SINGLE_PDF_NAME
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(pdf_path))
    window._export_pdf_to_path(config, printer)
    assert pdf_path.exists()

    windows_script_path = tmp_path / SINGLE_WINDOWS_SCRIPT_NAME
    window._export_windows_script_to_path(config, str(windows_script_path))
    assert windows_script_path.exists()

    macos_profile_path = tmp_path / SINGLE_MACOS_PROFILE_NAME
    window._export_macos_profile_to_path(config, str(macos_profile_path))
    assert macos_profile_path.exists()


def test_about_dialog(monkeypatch: MonkeyPatch, qtbot: QtBot) -> None:
    """Ensure the About dialog is invoked."""
    window = MainWindow()
    qtbot.addWidget(window)

    called = {"info": 0}

    def fake_info(*_args: Any, **_kwargs: Any) -> None:
        """Track information dialog calls."""
        called["info"] += 1

    monkeypatch.setattr("wifiqr.ui.main_window.QMessageBox.information", staticmethod(fake_info))
    window._show_about()
    assert called["info"] == 1


def test_button_label_shrink(qtbot: QtBot) -> None:
    """Ensure labels update when the window shrinks."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.print_button.setProperty("fullText", "X" * 200)
    window.resize(200, 200)
    window._update_button_labels()


def test_add_to_table_without_ssid(qtbot: QtBot) -> None:
    """Ensure blank SSIDs do not add table rows."""
    window = MainWindow()
    qtbot.addWidget(window)
    window._add_to_table()
    assert window.network_table.rowCount() == 0


def test_apply_table_column_widths_with_empty_cells(qtbot: QtBot) -> None:
    """Ensure column sizing handles empty rows."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.network_table.insertRow(0)
    window._apply_table_column_widths()


def test_table_item_changed_defaults(qtbot: QtBot) -> None:
    """Ensure missing table values are normalized."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()

    location_item = window.network_table.item(0, 0)
    ssid_item = window.network_table.item(0, 1)
    assert location_item is not None
    assert ssid_item is not None

    location_item.setText("")
    ssid_item.setText("")

    window._table_item_changed(location_item)
    window._table_item_changed(ssid_item)

    assert location_item.text() == "Unnamed"
    assert ssid_item.text() == "Unnamed"


def test_view_password_no_item_and_cancel(
    monkeypatch: MonkeyPatch,
    qtbot: QtBot,
) -> None:
    """Ensure view password no-ops on missing or canceled input."""
    window = MainWindow()
    qtbot.addWidget(window)
    window._view_password(0)

    _populate(window)
    window._add_to_table()
    monkeypatch.setattr(
        "wifiqr.ui.main_window.QInputDialog.getText",
        staticmethod(lambda *args, **kwargs: ("", False)),
    )
    window._view_password(0)


def test_password_widget_missing_parts(qtbot: QtBot) -> None:
    """Ensure password widget updates no-op on missing parts."""
    window = MainWindow()
    qtbot.addWidget(window)

    window._update_password_widget(0, DEFAULT_PASSWORD)
    window._toggle_password_visibility(0)

    _populate(window)
    window._add_to_table()
    window.network_table.removeCellWidget(0, 2)
    window._toggle_password_visibility(0)
    window.network_table.setCellWidget(0, 2, QWidget())
    window._update_password_widget(0, DEFAULT_PASSWORD)
    window._toggle_password_visibility(0)


def test_edit_ssid_missing(qtbot: QtBot) -> None:
    """Ensure edit SSID no-ops when a row is missing."""
    window = MainWindow()
    qtbot.addWidget(window)
    window._edit_ssid(0)


def test_row_to_config_missing_and_no_combo(qtbot: QtBot) -> None:
    """Ensure row conversion handles missing widgets."""
    window = MainWindow()
    qtbot.addWidget(window)
    assert window._row_to_config(0) is None

    _populate(window)
    window._add_to_table()
    # Remove the security combobox - config should still work with default
    window.network_table.removeCellWidget(0, 3)
    config = window._row_to_config(0)
    assert config is not None
    assert config.security == DEFAULT_SECURITY


def test_save_load_cancel_and_empty(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    qtbot: QtBot,
) -> None:
    """Ensure save/load cancel paths are handled."""
    window = MainWindow()
    qtbot.addWidget(window)

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(lambda *args, **kwargs: ("", "")),
    )
    window._save()
    window._save_as()

    window.location_input.setText("Solo")
    window.ssid_input.setText("SoloSSID")
    save_path = tmp_path / "single.json"
    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(save_path), "")),
    )
    window._save_as()
    assert save_path.exists()

    monkeypatch.setattr(
        "wifiqr.ui.main_window.QFileDialog.getOpenFileName",
        staticmethod(lambda *args, **kwargs: ("", "")),
    )
    window._load()


def test_obfuscate_empty(qtbot: QtBot) -> None:
    """Ensure obfuscation returns empty for blank passwords."""
    window = MainWindow()
    qtbot.addWidget(window)
    assert window._obfuscate_password("") == ""


def test_save_existing_path(tmp_path: Path, qtbot: QtBot) -> None:
    """Ensure save uses an existing path when set."""
    window = MainWindow()
    qtbot.addWidget(window)
    _populate(window)
    window._add_to_table()
    save_path = tmp_path / "existing.json"
    window._current_save_path = str(save_path)
    window._save()
    assert save_path.exists()
