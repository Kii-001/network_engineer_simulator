"""Perangkat Switch Layer 2 standar dengan tabel MAC Address dan flooding."""
from __future__ import annotations

import time
from devices.base_device import BaseDevice


class Switch(BaseDevice):
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        super().__init__(device_id, dtype, spec, name, x, y, rotation)
        # mac_table: {mac_str: {"port": port_name, "vlan": vlan_id, "time": timestamp}}
        self.mac_table: dict[str, dict] = {}
        self.mac_timeout: float = 300.0

    def learn_mac(self, mac: str, port_name: str, vlan_id: int = 1) -> None:
        self.mac_table[mac.upper()] = {
            "port": port_name,
            "vlan": vlan_id,
            "time": time.time(),
        }

    def lookup_mac(self, mac: str, vlan_id: int = 1) -> str | None:
        entry = self.mac_table.get(mac.upper())
        if entry:
            return entry["port"]
        return None

    def clear_mac_table(self) -> None:
        self.mac_table.clear()

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.mac_table:
            d["mac_table"] = [
                {"mac": mac, "port": v["port"], "vlan": v["vlan"]}
                for mac, v in self.mac_table.items()
            ]
        return d
