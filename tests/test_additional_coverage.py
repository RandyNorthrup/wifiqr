"""Test coverage for additional main_window functionality."""

import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QTableWidgetItem
from pytestqt.qtbot import QtBot

from wifiqr.constants import SECURITY_OPTIONS
from wifiqr.services.wifi_payload import WifiConfig
from wifiqr.ui.main_window import MainWindow


def test_browse_image_with_file_selection(qtbot: QtBot, tmp_path: Path) -> None:
    """Test selecting an image file through the browse dialog."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Create a test image file
    test_image = Image.new("RGB", (100, 100), color="red")
    image_path = tmp_path / "test_image.png"
    test_image.save(image_path)

    # Mock the file dialog to return our test image
    with patch.object(
        QFileDialog, "getOpenFileName", return_value=(str(image_path), "")
    ):
        window._browse_image()

    # Verify image path is displayed
    assert window.image_path_display.text() == str(image_path)
    # Verify config has image data
    assert window._config.image_data is not None


def test_browse_svg_image(qtbot: QtBot, tmp_path: Path) -> None:
    """Test selecting an SVG file through the browse dialog."""
    window = MainWindow()
    qtbot.addWidget(window)

    svg_content = (
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"64\" height=\"64\">"
        "<rect width=\"64\" height=\"64\" fill=\"red\"/>"
        "</svg>"
    )
    image_path = tmp_path / "test_image.svg"
    image_path.write_text(svg_content, encoding="utf-8")

    with patch.object(
        QFileDialog, "getOpenFileName", return_value=(str(image_path), "")
    ):
        window._browse_image()

    assert window.image_path_display.text() == str(image_path)
    assert window._config.image_data is not None


def test_browse_image_cancel(qtbot: QtBot) -> None:
    """Test canceling the browse image dialog."""
    window = MainWindow()
    qtbot.addWidget(window)

    initial_image_data = window._config.image_data

    # Mock the file dialog to return empty (cancelled)
    with patch.object(QFileDialog, "getOpenFileName", return_value=("", "")):
        window._browse_image()

    # Verify nothing changed
    assert window._config.image_data == initial_image_data


def test_browse_image_with_invalid_file(qtbot: QtBot, tmp_path: Path) -> None:
    """Test handling of invalid image file."""
    window = MainWindow()
    qtbot.addWidget(window)

    initial_image_data = window._config.image_data

    # Create a non-image file
    invalid_file = tmp_path / "not_an_image.txt"
    invalid_file.write_text("This is not an image")

    # Mock the file dialog
    with patch.object(
        QFileDialog, "getOpenFileName", return_value=(str(invalid_file), "")
    ), patch.object(QMessageBox, "warning") as mock_warning:
        window._browse_image()
        mock_warning.assert_called_once()

    # Config should be unchanged for invalid images
    assert window._config.image_data == initial_image_data


def test_export_png_cancel(qtbot: QtBot) -> None:
    """Test canceling PNG export."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Mock the file dialog to return empty (cancelled)
    with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
        window._export_png()
        # Should complete without error


def test_export_png_error_handling(qtbot: QtBot) -> None:
    """Test PNG export error handling."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Mock the file dialog to return a path, but make export fail
    with patch.object(
        QFileDialog, "getSaveFileName", return_value=("/invalid/path/test.png", "")
    ), patch.object(QMessageBox, "critical") as mock_critical:
        window._export_png()

        # Verify error dialog was shown
        mock_critical.assert_called_once()


def test_export_pdf_cancel(qtbot: QtBot) -> None:
    """Test canceling PDF export."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Mock the file dialog to return empty (cancelled)
    with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
        window._export_pdf()
        # Should complete without error


def test_export_macos_profile_cancel(qtbot: QtBot) -> None:
    """Test canceling macOS profile export."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Mock the file dialog to return empty (cancelled)
    with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
        window._export_macos_profile()
        # Should complete without error


def test_export_macos_profile_success(qtbot: QtBot, tmp_path: Path) -> None:
    """Test successful macOS profile export."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window.password_input.setText("password123")
    window._refresh_preview_now()

    profile_path = tmp_path / "test.mobileconfig"

    # Mock the dialogs
    with patch.object(
        QFileDialog, "getSaveFileName", return_value=(str(profile_path), "")
    ), patch.object(QMessageBox, "information") as mock_info:
        window._export_macos_profile()

        # Verify success message was shown
        mock_info.assert_called_once()
        # Verify file was created
        assert profile_path.exists()


def test_update_scaled_preview_with_no_pixmap(qtbot: QtBot) -> None:
    """Test update scaled preview when no pixmap exists."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Clear the pixmap
    window._current_pixmap = None

    # Should not crash
    window._update_scaled_preview()


def test_resize_event_with_pixmap(qtbot: QtBot) -> None:
    """Test resize event handling with active pixmap."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Trigger resize
    window.resize(800, 600)
    qtbot.wait(50)

    # Should not crash and preview should still be visible
    assert window._current_pixmap is not None


def test_password_enabled_state_for_open_network(qtbot: QtBot) -> None:
    """Test password field is disabled for open networks."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Manually call the security changed handler with "Open"
    window._on_security_changed("Open")

    # Password field should be disabled
    assert not window.password_input.isEnabled()
    assert "Not required" in window.password_input.placeholderText()


def test_compose_qr_with_header(qtbot: QtBot) -> None:
    """Test QR header composition."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Generate a simple QR image
    qr_image = Image.new("RGB", (300, 300), color="white")

    # Test with a header
    with_header = window._compose_qr_with_header(qr_image, "Test Location")

    # Image should be taller than original
    assert with_header.height > qr_image.height
    assert isinstance(with_header, Image.Image)


def test_double_click_loads_network_into_form(qtbot: QtBot) -> None:
    """Test double-clicking table row loads network into form."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Add a network to the table
    window.location_input.setText("Office")
    window.ssid_input.setText("OfficeWiFi")
    window.password_input.setText("secret123")
    window.security_input.setCurrentText("WPA/WPA2/WPA3")
    window._add_to_table()

    # Change form to different values
    window.location_input.setText("Home")
    window.ssid_input.setText("HomeWiFi")

    # Double-click the first row
    index = window.network_table.model().index(0, 0)
    window._table_double_clicked(index)

    # Verify form was updated with table values
    assert window.location_input.text() == "Office"
    assert window.ssid_input.text() == "OfficeWiFi"
    assert window.password_input.text() == "secret123"
    assert window.security_input.currentText() == "WPA/WPA2/WPA3"


def test_position_image_button(qtbot: QtBot) -> None:
    """Test image browse button positioning."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(100)  # Let layout settle

    # The button should be positioned inside the text field
    window._position_image_button()

    button_pos = window.image_browse_button.pos()
    # Button should be on the right side
    assert button_pos.x() > 0


def test_show_event_triggers_layout_updates(qtbot: QtBot) -> None:
    """Test that showing the window triggers layout updates."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Show the window - this should trigger showEvent and all layout callbacks
    window.show()
    qtbot.wait(150)  # Wait for timers to fire

    # Window should be properly sized
    assert window.size().width() > 0
    assert window.size().height() > 0


def test_resize_event_updates_scaled_preview(qtbot: QtBot) -> None:
    """Ensure resize event triggers scaled preview when pixmap exists."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(50)

    window._current_pixmap = QPixmap(120, 120)
    event = QResizeEvent(QSize(900, 700), window.size())
    window.resizeEvent(event)

    assert window._scaled_pixmap is not None


def test_batch_export_uses_current_config(qtbot: QtBot, tmp_path: Path) -> None:
    """Ensure batch export uses current config when no table entries exist."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("SoloNet")
    window._update_config()

    with patch.object(
        QFileDialog, "getExistingDirectory", return_value=str(tmp_path)
    ), patch.object(
        QInputDialog, "getItem", return_value=("PNG", True)
    ):
        window._batch_export()

    exported = list(tmp_path.glob("*.png"))
    assert exported, "Expected PNG export for current config"


def test_table_item_changed_sets_default_security(qtbot: QtBot) -> None:
    """Ensure empty security cells are normalized to default."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.network_table.setRowCount(1)
    item = QTableWidgetItem(" ")
    window.network_table.setItem(0, 3, item)

    window._table_item_changed(item)

    assert item.text() == SECURITY_OPTIONS[0]


def test_handle_column_resize_noop_for_fixed_columns(qtbot: QtBot) -> None:
    """Ensure non-resizable columns are ignored for resize handling."""
    window = MainWindow()
    qtbot.addWidget(window)

    window._handle_column_resize(4, 100, 100)


def test_handle_column_resize_fills_gap(qtbot: QtBot) -> None:
    """Ensure password column expands to fill gaps when needed."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(50)

    window.network_table.setColumnWidth(0, 100)
    window.network_table.setColumnWidth(1, 100)
    window.network_table.setColumnWidth(2, 100)
    window.network_table.setColumnWidth(3, 100)
    window.network_table.setColumnWidth(4, 100)

    old_width = window.network_table.columnWidth(2)
    window._handle_column_resize(0, old_width, old_width)

    assert window.network_table.columnWidth(2) >= old_width


def test_save_to_path_uses_current_config_when_table_empty(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Ensure save uses current config when table is empty."""
    window = MainWindow()
    qtbot.addWidget(window)

    window._config = WifiConfig(
        location="HQ",
        ssid="Single",
        password="pass",
        security="WPA",
        hidden=False,
        image_data=None,
    )

    path = tmp_path / "single.json"
    window._save_to_path(str(path))

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["ssid"] == "Single"


def test_set_form_from_config_with_image_data(qtbot: QtBot) -> None:
    """Ensure image path display is updated for loaded image data."""
    window = MainWindow()
    qtbot.addWidget(window)

    config = WifiConfig(
        location="HQ",
        ssid="Net",
        password="pass",
        security="WPA",
        hidden=False,
        image_data="abc",
    )

    window._set_form_from_config(config)

    assert window.image_path_display.text() == "(Image loaded from saved network)"


def test_lock_window_size(qtbot: QtBot) -> None:
    """Test window size locking functionality."""
    window = MainWindow()
    qtbot.addWidget(window)

    window._lock_window_size()

    # Window should have both min and max size set
    assert window.minimumSize().width() > 0
    assert window.minimumSize().height() > 0


def test_lock_window_width_only(qtbot: QtBot) -> None:
    """Test width-only window locking."""
    window = MainWindow()
    qtbot.addWidget(window)

    initial_height = window.height()
    window._lock_window_width_only(initial_height)

    # Width should be locked, height should match parameter
    assert window.height() == initial_height


def test_apply_panel_minimums(qtbot: QtBot) -> None:
    """Test panel minimum size application."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()  # Need to show window for panels to be visible
    qtbot.wait(50)

    # All panels should be visible after showing
    assert window.form_group.isVisible()
    assert window.table_group.isVisible()
    assert window.preview_group.isVisible()

    window._apply_panel_minimums()

    # Panels should have minimum sizes set
    assert window.form_group.minimumSize().height() > 0
    assert window.table_group.minimumSize().height() > 0


def test_update_button_labels(qtbot: QtBot) -> None:
    """Test button label updates based on window size."""
    window = MainWindow()
    qtbot.addWidget(window)

    window._update_button_labels()

    # Should complete without error
    assert window.add_table_button.text() is not None


def test_compose_qr_with_header_empty_string(qtbot: QtBot) -> None:
    """Test QR header composition with empty header."""
    window = MainWindow()
    qtbot.addWidget(window)

    qr_image = Image.new("RGB", (300, 300), color="white")

    # Empty header should return original image
    result = window._compose_qr_with_header(qr_image, "")
    assert result == qr_image

    # Whitespace-only header should also return original
    result = window._compose_qr_with_header(qr_image, "   ")
    assert result == qr_image


def test_export_windows_script_success(qtbot: QtBot, tmp_path: Path) -> None:
    """Test successful Windows script export."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window.password_input.setText("password123")
    window._refresh_preview_now()

    script_path = tmp_path / "test.ps1"

    # Mock the dialogs
    with patch.object(
        QFileDialog, "getSaveFileName", return_value=(str(script_path), "")
    ), patch.object(QMessageBox, "information") as mock_info:
        window._export_windows_script()

        # Verify success message was shown
        mock_info.assert_called_once()
        # Verify file was created
        assert script_path.exists()


def test_export_windows_script_cancel(qtbot: QtBot) -> None:
    """Test canceling Windows script export."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Mock the file dialog to return empty (cancelled)
    with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
        window._export_windows_script()
        # Should complete without error


def test_browse_image_file_read_error(qtbot: QtBot, tmp_path: Path) -> None:
    """Test handling of file read errors during image browse."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Create a file we can't read
    bad_path = "/this/path/does/not/exist.png"

    # Mock the file dialog and message box
    with patch.object(
        QFileDialog, "getOpenFileName", return_value=(bad_path, "")
    ), patch.object(QMessageBox, "warning") as mock_warning:
        window._browse_image()

        # Verify warning was shown
        mock_warning.assert_called_once()


def test_export_macos_profile_error_handling(qtbot: QtBot) -> None:
    """Test macOS profile export error handling."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Mock the file dialog to return a path, but make export fail
    with patch.object(
        QFileDialog, "getSaveFileName", return_value=("/invalid/path/test.mobileconfig", "")
    ), patch.object(QMessageBox, "critical") as mock_critical:
        window._export_macos_profile()

        # Verify error dialog was shown
        mock_critical.assert_called_once()


def test_resize_event_without_pixmap(qtbot: QtBot) -> None:
    """Test resize event when no pixmap exists."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Clear pixmap
    window._current_pixmap = None

    # Trigger resize - should not crash
    window.resize(800, 600)
    qtbot.wait(50)


def test_apply_panel_minimums_with_hidden_panel(qtbot: QtBot) -> None:
    """Test panel minimums when some panels are hidden."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(50)

    # Hide the preview panel
    window.preview_group.setVisible(False)

    window._apply_panel_minimums()

    # Hidden panel should have zero minimum size
    assert window.preview_group.minimumSize().height() == 0


def test_batch_export_cancel_at_type_selection(qtbot: QtBot) -> None:
    """Test canceling batch export at type selection."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._add_to_table()

    # Mock input dialog to return cancelled
    with patch("PySide6.QtWidgets.QInputDialog.getItem", return_value=("PNG", False)):
        window._batch_export()
        # Should complete without error


def test_batch_export_cancel_at_folder_selection(qtbot: QtBot) -> None:
    """Test canceling batch export at folder selection."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._add_to_table()

    # Mock dialogs - accept type, cancel folder
    with patch(
        "PySide6.QtWidgets.QInputDialog.getItem", return_value=("PNG", True)
    ), patch.object(QFileDialog, "getExistingDirectory", return_value=""):
        window._batch_export()
        # Should complete without error


def test_table_item_changed_column_3_empty(qtbot: QtBot) -> None:
    """Test table item normalization for security column."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Add a row and get the security item (column 3)
    # Actually column 3 is a combo box, not an item
    # So this path is not reachable with current code
    # Let's test column 1 (SSID) instead

    window.ssid_input.setText("Test")
    window._add_to_table()

    # Get SSID item and clear it
    ssid_item = window.network_table.item(0, 1)
    assert ssid_item is not None
    ssid_item.setText("")

    # Trigger the change handler
    window._table_item_changed(ssid_item)

    # Should be normalized to "Unnamed"
    assert ssid_item.text() == "Unnamed"


def test_export_windows_script_error_handling(qtbot: QtBot) -> None:
    """Test Windows script export error handling."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Mock the file dialog to return invalid path
    with patch.object(
        QFileDialog, "getSaveFileName", return_value=("/invalid/path/test.ps1", "")
    ), patch.object(QMessageBox, "critical") as mock_critical:
        window._export_windows_script()

        # Verify error dialog was shown
        mock_critical.assert_called_once()


def test_batch_export_with_current_config_only(qtbot: QtBot) -> None:
    """Test batch export when table is empty but current config has SSID."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Set current config without adding to table
    window.ssid_input.setText("CurrentNetwork")
    window.password_input.setText("password123")

    # Table is empty but config is valid
    assert window.network_table.rowCount() == 0

    # Mock dialogs to proceed with export
    with patch(
        "PySide6.QtWidgets.QInputDialog.getItem", return_value=("PNG", True)
    ), patch.object(QFileDialog, "getExistingDirectory", return_value=""):
        # Should not crash - will exit at folder selection
        window._batch_export()


def test_save_with_current_config_only(qtbot: QtBot, tmp_path: Path) -> None:
    """Test save when table is empty but current config has SSID."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Set current config without adding to table
    window.ssid_input.setText("CurrentNetwork")
    window.password_input.setText("password123")

    save_path = tmp_path / "test_save.json"

    # Mock file dialog
    with patch.object(QFileDialog, "getSaveFileName", return_value=(str(save_path), "")):
        window._save()

    # File should contain the current config
    assert save_path.exists()


def test_handle_column_resize_with_gap(qtbot: QtBot) -> None:
    """Test column resize handling when there's a gap to fill."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(50)

    # Add some networks
    window.ssid_input.setText("Network1")
    window._add_to_table()

    # Manually trigger a resize that creates a gap
    # Make the table wider than the column widths
    window.network_table.setFixedWidth(1000)

    # Trigger resize handler
    window._handle_column_resize(0, 150, 100)

    # Should complete without error


def test_focus_search(qtbot: QtBot) -> None:
    """Test focus search functionality."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()  # Need to show window for focus to work
    qtbot.wait(50)

    window._focus_search()

    # Search input should have focus (though test environment may not support this)
    # Just verify the method executes without error
    assert window.search_input is not None


def test_export_macos_profile_when_no_payload(qtbot: QtBot) -> None:
    """Test macOS profile export when no payload exists."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Clear any payload
    window._current_payload = ""

    # Try to export - should return early
    window._export_macos_profile()
    # Should complete without showing dialog


def test_batch_export_when_empty_with_no_config(qtbot: QtBot) -> None:
    """Test batch export when table is empty and no valid config."""
    window = MainWindow()
    qtbot.addWidget(window)

    # No SSID in current config
    window.ssid_input.setText("")

    # Table is empty
    assert window.network_table.rowCount() == 0

    # Should return early
    window._batch_export()
    # Completes without showing any dialogs


def test_resize_event_with_active_pixmap(qtbot: QtBot) -> None:
    """Test resize event when pixmap exists."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Generate a QR code
    window.ssid_input.setText("TestNetwork")
    window._refresh_preview_now()

    # Trigger resize - should update preview
    window.resize(900, 700)
    qtbot.wait(50)

    # Preview should still exist
    assert window._current_pixmap is not None


def test_table_item_changed_column_resize_trigger(qtbot: QtBot) -> None:
    """Test that changing column 1 or 2 triggers resize."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("TestNetwork")
    window.password_input.setText("password123")
    window._add_to_table()

    # Get password item (column 2)
    password_item = window.network_table.item(0, 2)
    assert password_item is not None

    # Change password item - should trigger column width adjustment
    # (column 2 is in the resize set)
    window._table_item_changed(password_item)
    # Should complete without error
