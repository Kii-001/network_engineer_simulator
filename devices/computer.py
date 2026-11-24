"""Perangkat Komputer / Host: PC, Laptop, Printer."""
from __future__ import annotations

from devices.base_device import BaseDevice
from networking.arp import ARPTable
from networking.ip_address import ip_to_str, parse_ip


class Computer(BaseDevice):
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        super().__init__(device_id, dtype, spec, name, x, y, rotation)
        self.arp_table = ARPTable()
        self.dhcp_client: bool = False
        self.dns_server: int | None = None
        self.wireless_connected_to: str | None = None  # SSID yang terhubung jika Laptop/Wireless

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["dhcp_client"] = self.dhcp_client
        d["dns_server"] = ip_to_str(self.dns_server) if self.dns_server is not None else None
        d["wireless_connected_to"] = self.wireless_connected_to
        return d
