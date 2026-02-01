"""UI widget behavior tests."""

import cv2
import numpy as np
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QPixmap
from pytestqt.qtbot import QtBot

from wifiqr.ui.main_window import MainWindow


def _decode_qr_from_pixmap(pixmap: QPixmap) -> str:
    """Extract and decode QR code from a QPixmap."""
    # Convert QPixmap to numpy array via QBuffer
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()

    # Get bytes and convert to numpy array for OpenCV
    image_bytes = buffer.data().data()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Decode QR code using OpenCV
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(img)  # type: ignore[arg-type]

    if not data:
        raise ValueError("No QR code found in image")

    return data



def test_tooltips_present(qtbot: QtBot) -> None:
    """Ensure key widgets expose tooltips."""
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.ssid_input.toolTip()
    assert window.location_input.toolTip()
    assert window.password_input.toolTip()
    assert window.security_input.toolTip()
    assert window.hidden_input.toolTip()
    assert window.print_button.toolTip()
    assert window.export_png_button.toolTip()
    assert window.export_pdf_button.toolTip()
    assert window.export_script_button.toolTip()
    assert window.export_macos_button.toolTip()
    assert window.batch_export_button.toolTip()
    assert window.add_table_button.toolTip()
    assert window.search_input.toolTip()
    assert window.search_up_button.toolTip()
    assert window.search_down_button.toolTip()
    assert window.delete_table_button.toolTip()


def test_hidden_network_updates_payload(qtbot: QtBot) -> None:
    """Ensure hidden network toggles update QR payload text."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("HiddenSSID")
    window.password_input.setText("secret")
    window.security_input.setCurrentText("WPA/WPA2/WPA3")

    window.hidden_input.setChecked(True)
    qtbot.waitUntil(lambda: "H:true" in window.payload_label.text())

    window.hidden_input.setChecked(False)
    qtbot.waitUntil(lambda: "H:false" in window.payload_label.text())


def test_preview_toggle_updates_panels(qtbot: QtBot) -> None:
    """Ensure preview panel hides and shows when toggled."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.preview_toggle.setChecked(False)
    assert window.preview_group.isHidden() is True

    window.preview_toggle.setChecked(True)
    assert window.preview_group.isHidden() is False


def test_qr_code_matches_input_details(qtbot: QtBot) -> None:
    """Verify QR code content matches entered network details."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Enter network details
    window.ssid_input.setText("TestNetwork")
    window.password_input.setText("password123")
    window.security_input.setCurrentText("WPA/WPA2/WPA3")
    window.hidden_input.setChecked(False)
    window._refresh_preview_now()

    # Get the generated QR code
    pixmap = window._current_pixmap
    assert pixmap is not None

    # Decode and verify
    decoded = _decode_qr_from_pixmap(pixmap)
    assert decoded == "WIFI:T:WPA;S:TestNetwork;P:password123;H:false;;"

    # Verify it also matches the payload text
    assert window.payload_label.text() == decoded


def test_qr_updates_when_password_changes(qtbot: QtBot) -> None:
    """Verify QR code updates when password field changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Initial setup
    window.ssid_input.setText("MyWiFi")
    window.password_input.setText("initial")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    initial_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "P:initial" in initial_qr

    # Change password
    window.password_input.setText("updated")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    updated_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "P:updated" in updated_qr
    assert initial_qr != updated_qr


def test_qr_updates_when_ssid_changes(qtbot: QtBot) -> None:
    """Verify QR code updates when SSID field changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Initial setup
    window.ssid_input.setText("FirstNetwork")
    window.password_input.setText("pass")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    initial_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "S:FirstNetwork" in initial_qr

    # Change SSID
    window.ssid_input.setText("SecondNetwork")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    updated_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "S:SecondNetwork" in updated_qr
    assert initial_qr != updated_qr


def test_qr_updates_when_security_changes(qtbot: QtBot) -> None:
    """Verify QR code updates when security type changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Initial setup with WPA
    window.ssid_input.setText("SecureNet")
    window.password_input.setText("secret")
    window.security_input.setCurrentText("WPA/WPA2/WPA3")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    wpa_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "T:WPA" in wpa_qr

    # Change to WEP
    window.security_input.setCurrentText("WEP")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    wep_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "T:WEP" in wep_qr
    assert wpa_qr != wep_qr


def test_qr_updates_when_hidden_changes(qtbot: QtBot) -> None:
    """Verify QR code updates when hidden network toggle changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    # Initial setup not hidden
    window.ssid_input.setText("VisibleNet")
    window.password_input.setText("pass")
    window.hidden_input.setChecked(False)
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    visible_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "H:false" in visible_qr

    # Make it hidden
    window.hidden_input.setChecked(True)
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    hidden_qr = _decode_qr_from_pixmap(current_pixmap)
    assert "H:true" in hidden_qr
    assert visible_qr != hidden_qr

