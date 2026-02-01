"""Service layer unit tests."""

from pathlib import Path

from pytestqt.qtbot import QtBot

from wifiqr.services.export_service import pil_to_qimage, pil_to_qpixmap
from wifiqr.services.macos_profile import (
    build_macos_mobileconfig,
    build_macos_mobileconfig_multi,
)
from wifiqr.services.qr_service import generate_qr_image, save_qr_image
from wifiqr.services.wifi_payload import WifiConfig, build_wifi_payload
from wifiqr.services.wifi_profiles import build_wlan_profile_xml
from wifiqr.services.windows_script import (
    build_windows_connect_script,
    build_windows_connect_script_multi,
)

SAMPLE_QR_PAYLOAD = "WIFI:T:WPA;S:Test;P:pass;H:false;;"
QR_IMAGE_SIZE_LARGE = 320
QR_IMAGE_SIZE_STANDARD = 128
QR_IMAGE_SIZE_SMALL = 64
GRAYSCALE_VALUE = 128


def test_build_wifi_payload_wep() -> None:
    """Ensure WEP payloads encode correctly."""
    config = WifiConfig(
        location="Lab",
        ssid="Legacy",
        password="abc123",
        security="WEP",
        hidden=False,
    )
    payload = build_wifi_payload(config)
    assert payload == "WIFI:T:WEP;S:Legacy;P:abc123;H:false;;"


def test_build_wifi_payload_nopass_alias() -> None:
    """Ensure nopass aliases map to open payloads."""
    config = WifiConfig(
        location="Cafe",
        ssid="Cafe",
        password="",
        security="nopass",
        hidden=False,
    )
    payload = build_wifi_payload(config)
    assert payload == "WIFI:T:nopass;S:Cafe;H:false;;"


def test_generate_qr_image_size() -> None:
    """Ensure generated QR image sizes are respected."""
    image = generate_qr_image(
        SAMPLE_QR_PAYLOAD,
        size=QR_IMAGE_SIZE_LARGE,
    )
    assert image.size == (QR_IMAGE_SIZE_LARGE, QR_IMAGE_SIZE_LARGE)


def test_save_qr_image(tmp_path: Path) -> None:
    """Ensure QR images can be saved to disk."""
    image = generate_qr_image("data", size=QR_IMAGE_SIZE_STANDARD)
    out = tmp_path / "qr.png"
    save_qr_image(image, str(out))
    assert out.exists()


def test_export_service_conversions(qtbot: QtBot) -> None:
    """Ensure PIL-to-Qt conversions preserve dimensions."""
    image = generate_qr_image("data", size=QR_IMAGE_SIZE_STANDARD)
    qt_image = pil_to_qimage(image)
    qt_pixmap = pil_to_qpixmap(image)
    assert qt_image.width() == QR_IMAGE_SIZE_STANDARD
    assert qt_pixmap.width() == QR_IMAGE_SIZE_STANDARD

    from PIL import Image

    gray_image = Image.new(
        "L",
        (QR_IMAGE_SIZE_SMALL, QR_IMAGE_SIZE_SMALL),
        color=GRAYSCALE_VALUE,
    )
    qt_gray_image = pil_to_qimage(gray_image)
    assert qt_gray_image.width() == QR_IMAGE_SIZE_SMALL


def test_windows_script_contains_ssid() -> None:
    """Ensure the generated script references the SSID."""
    config = WifiConfig(
        location="HQ",
        ssid="Office",
        password="secret",
        security="WPA",
        hidden=False,
    )
    windows_script_export = build_windows_connect_script(config)
    assert "netsh wlan connect name=\"Office\"" in windows_script_export.content


def test_windows_script_multi() -> None:
    """Ensure multi-network scripts include all profiles and final connect."""
    configs = [
        WifiConfig(
            location="HQ",
            ssid="Office",
            password="secret",
            security="WPA",
            hidden=False,
        ),
        WifiConfig(
            location="Lab",
            ssid="LabNet",
            password="abc123",
            security="WEP",
            hidden=False,
        ),
    ]
    windows_script_export = build_windows_connect_script_multi(configs)
    assert "wifi-profile-1.xml" in windows_script_export.content
    assert "wifi-profile-2.xml" in windows_script_export.content
    assert "netsh wlan connect name=\"LabNet\"" in windows_script_export.content


def test_windows_script_multi_empty() -> None:
    """Ensure an empty multi-script request errors."""
    try:
        build_windows_connect_script_multi([])
        raise AssertionError("Expected ValueError for empty configs")
    except ValueError:
        assert True


def test_macos_mobileconfig_open() -> None:
    """Ensure open networks map to the correct macOS encryption type."""
    config = WifiConfig(
        location="Lobby",
        ssid="Guest",
        password="",
        security="None",
        hidden=False,
    )
    profile = build_macos_mobileconfig(config)
    assert "<key>EncryptionType</key><string>None</string>" in profile.content


def test_macos_mobileconfig_wep() -> None:
    """Ensure WEP networks map to the correct macOS encryption type."""
    config = WifiConfig(
        location="Lab",
        ssid="Legacy",
        password="abc123",
        security="WEP",
        hidden=False,
    )
    profile = build_macos_mobileconfig(config)
    assert "<key>EncryptionType</key><string>WEP</string>" in profile.content


def test_macos_mobileconfig_multi() -> None:
    """Ensure multi-network profiles contain all payloads."""
    configs = [
        WifiConfig(
            location="HQ",
            ssid="Office",
            password="secret",
            security="WPA",
            hidden=True,
        ),
        WifiConfig(
            location="Lobby",
            ssid="Guest",
            password="",
            security="None",
            hidden=False,
        ),
    ]
    profile = build_macos_mobileconfig_multi(configs)
    assert profile.content.count("com.apple.wifi.managed") == 2


def test_macos_mobileconfig_multi_wep_and_empty() -> None:
    """Ensure multi-network WEP profiles render and empty lists fail."""
    configs = [
        WifiConfig(
            location="Lab",
            ssid="Legacy",
            password="abc123",
            security="WEP",
            hidden=False,
        ),
    ]
    profile = build_macos_mobileconfig_multi(configs)
    assert "<key>EncryptionType</key><string>WEP</string>" in profile.content

    try:
        build_macos_mobileconfig_multi([])
        raise AssertionError("Expected ValueError for empty configs")
    except ValueError:
        assert True


def test_wlan_profile_xml_escape() -> None:
    """Ensure XML escaping is applied to SSID and password values."""
    config = WifiConfig(
        location="HQ",
        ssid="AC&ME",
        password="p<>",
        security="WPA",
        hidden=False,
    )
    wlan_profile_xml = build_wlan_profile_xml(config)
    assert "AC&amp;ME" in wlan_profile_xml
    assert "p&lt;&gt;" in wlan_profile_xml
