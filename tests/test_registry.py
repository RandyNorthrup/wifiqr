"""Registry-level export tests."""

from wifiqr.services.macos_profile import build_macos_mobileconfig
from wifiqr.services.wifi_payload import WifiConfig
from wifiqr.services.wifi_profiles import build_wlan_profile_xml
from wifiqr.services.windows_script import build_windows_connect_script


def test_profile_xml_open_network() -> None:
    """Ensure open network profiles omit shared keys."""
    config = WifiConfig(
        location="Lobby",
        ssid="Guest",
        password="",
        security="None",
        hidden=False,
    )
    wlan_profile_xml = build_wlan_profile_xml(config)
    assert "<authentication>open</authentication>" in wlan_profile_xml
    assert "<encryption>none</encryption>" in wlan_profile_xml
    assert "<sharedKey>" not in wlan_profile_xml


def test_profile_xml_wpa() -> None:
    """Ensure WPA profiles include shared keys and non-broadcast tags."""
    config = WifiConfig(
        location="HQ",
        ssid="Office",
        password="secret",
        security="WPA/WPA2/WPA3",
        hidden=True,
    )
    wlan_profile_xml = build_wlan_profile_xml(config)
    assert "<authentication>WPA2PSK</authentication>" in wlan_profile_xml
    assert "<encryption>AES</encryption>" in wlan_profile_xml
    assert "<nonBroadcast>true</nonBroadcast>" in wlan_profile_xml
    assert "<sharedKey>" in wlan_profile_xml


def test_profile_xml_wep() -> None:
    """Ensure WEP profiles use the networkKey type."""
    config = WifiConfig(
        location="Lab",
        ssid="Legacy",
        password="abc123",
        security="WEP",
        hidden=False,
    )
    wlan_profile_xml = build_wlan_profile_xml(config)
    assert "<encryption>WEP</encryption>" in wlan_profile_xml
    assert "<keyType>networkKey</keyType>" in wlan_profile_xml


def test_windows_connect_script() -> None:
    """Ensure Windows scripts include the connect command."""
    config = WifiConfig(
        location="HQ",
        ssid="Office",
        password="secret",
        security="WPA/WPA2/WPA3",
        hidden=False,
    )
    script = build_windows_connect_script(config)
    assert "netsh wlan add profile" in script.content
    assert "netsh wlan connect name=\"Office\"" in script.content


def test_macos_profile_export() -> None:
    """Ensure macOS profiles include SSID and hidden network tags."""
    config = WifiConfig(
        location="HQ",
        ssid="Office",
        password="secret",
        security="WPA/WPA2/WPA3",
        hidden=True,
    )
    profile = build_macos_mobileconfig(config)
    assert "com.apple.wifi.managed" in profile.content
    assert "<key>SSID_STR</key><string>Office</string>" in profile.content
    assert "<key>HIDDEN_NETWORK</key><true/>" in profile.content
