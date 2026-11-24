"""Perangkat Wireless Access Point (WAP): SSID, WPA2/WPA3, wireless association."""
from __future__ import annotations

from devices.base_device import BaseDevice


class AccessPoint(BaseDevice):
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        super().__init__(device_id, dtype, spec, name, x, y, rotation)
        self.ssid: str = f"NES_WiFi_{device_id}"
        self.security: str = "WPA2-PSK"   # 'OPEN' | 'WPA2-PSK' | 'WPA3-SAE'
        self.password: str = "network123"
        self.channel: int = 6
        self.associated_clients: set[str] = set()  # set of client MACs

    def associate(self, client_mac: str, password: str = "") -> bool:
        if self.security != "OPEN" and password != self.password:
            return False
        self.associated_clients.add(client_mac.upper())
        return True

    def disassociate(self, client_mac: str) -> None:
        self.associated_clients.discard(client_mac.upper())

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["wireless"] = {
            "ssid": self.ssid,
            "security": self.security,
            "password": self.password,
            "channel": self.channel,
        }
        return d
