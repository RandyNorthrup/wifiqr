"""Test preview updates in real-time."""

import base64
import io
from dataclasses import replace

import cv2
import numpy as np
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QPixmap
from pytestqt.qtbot import QtBot

from wifiqr.ui.main_window import MainWindow


def _decode_qr_from_pixmap(pixmap: QPixmap) -> str:
    """Extract and decode QR code from a QPixmap."""
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()

    image_bytes = buffer.data().data()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(img)  # type: ignore[arg-type]

    if not data:
        raise ValueError("No QR code found in image")

    return data


def test_preview_updates_on_location_change(qtbot: QtBot) -> None:
    """Verify preview updates when location changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("TestNet")
    window.location_input.setText("Office")
    window._refresh_preview_now()

    initial_pixmap = window._current_pixmap
    assert initial_pixmap is not None

    # Change location
    window.location_input.setText("Home")
    window._refresh_preview_now()

    updated_pixmap = window._current_pixmap
    # Pixmap should be different because header changed
    assert updated_pixmap is not initial_pixmap


def test_preview_updates_on_header_toggle(qtbot: QtBot) -> None:
    """Verify preview updates when header checkbox is toggled."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("TestNet")
    window.location_input.setText("Office")
    window.show_header_input.setChecked(True)
    window._refresh_preview_now()

    with_header_pixmap = window._current_pixmap
    assert with_header_pixmap is not None
    with_header_height = with_header_pixmap.height()

    # Toggle header off
    window.show_header_input.setChecked(False)
    window._refresh_preview_now()

    without_header_pixmap = window._current_pixmap
    assert without_header_pixmap is not None
    without_header_height = without_header_pixmap.height()

    # Pixmap with header should be taller
    assert with_header_height > without_header_height
    assert with_header_pixmap is not without_header_pixmap


def test_preview_updates_immediately_on_ssid_change(qtbot: QtBot) -> None:
    """Verify preview QR updates when SSID changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("Network1")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    qr1 = _decode_qr_from_pixmap(current_pixmap)
    assert "Network1" in qr1

    # Change SSID
    window.ssid_input.setText("Network2")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    qr2 = _decode_qr_from_pixmap(current_pixmap)
    assert "Network2" in qr2
    assert qr1 != qr2


def test_preview_updates_on_password_change(qtbot: QtBot) -> None:
    """Verify preview updates when password changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("TestNet")
    window.password_input.setText("pass1")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    qr1 = _decode_qr_from_pixmap(current_pixmap)
    assert "pass1" in qr1

    # Change password
    window.password_input.setText("pass2")
    window._refresh_preview_now()

    current_pixmap = window._current_pixmap
    assert current_pixmap is not None
    qr2 = _decode_qr_from_pixmap(current_pixmap)
    assert "pass2" in qr2
    assert qr1 != qr2


def test_preview_shows_header_when_enabled(qtbot: QtBot) -> None:
    """Verify header appears in preview when checkbox is checked."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("TestNet")
    window.location_input.setText("Office")
    window.show_header_input.setChecked(True)
    window._refresh_preview_now()

    # With header, pixmap should be taller than base QR
    with_header = window._current_pixmap
    assert with_header is not None

    window.show_header_input.setChecked(False)
    window._refresh_preview_now()

    without_header = window._current_pixmap
    assert without_header is not None

    assert with_header.height() > without_header.height()


def test_preview_updates_on_center_image_change(qtbot: QtBot) -> None:
    """Verify preview updates when center image data changes."""
    window = MainWindow()
    qtbot.addWidget(window)

    window.ssid_input.setText("TestNet")

    red = Image.new("RGB", (32, 32), color="red")
    buffer = io.BytesIO()
    red.save(buffer, format="PNG")
    red_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    window._config = replace(window._config, image_data=red_data)
    window._refresh_preview_now()

    red_pixmap = window._current_pixmap
    assert red_pixmap is not None

    blue = Image.new("RGB", (32, 32), color="blue")
    buffer = io.BytesIO()
    blue.save(buffer, format="PNG")
    blue_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    window._config = replace(window._config, image_data=blue_data)
    window._refresh_preview_now()

    blue_pixmap = window._current_pixmap
    assert blue_pixmap is not None
    assert blue_pixmap is not red_pixmap
