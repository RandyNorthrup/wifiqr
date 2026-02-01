"""Payload construction tests."""

from wifiqr.services.wifi_payload import (
    WifiConfig,
    build_wifi_payload,
    is_open_security,
)


def test_build_wifi_payload_wpa() -> None:
    """Ensure WPA payloads include a password field."""
    config = WifiConfig(
        location="HQ",
        ssid="Office",
        password="secret",
        security="WPA",
        hidden=False,
    )
    payload = build_wifi_payload(config)
    assert payload == "WIFI:T:WPA;S:Office;P:secret;H:false;;"


def test_build_wifi_payload_open() -> None:
    """Ensure open networks omit the password field."""
    config = WifiConfig(
        location="Lobby",
        ssid="Guest",
        password="",
        security="None",
        hidden=True,
    )
    payload = build_wifi_payload(config)
    assert payload == "WIFI:T:nopass;S:Guest;H:true;;"


def test_is_open_security_aliases() -> None:
    """Ensure open security aliases normalize to open."""
    assert is_open_security("open") is True
    assert is_open_security("WPA") is False
