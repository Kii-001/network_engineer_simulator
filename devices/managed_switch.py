"""Perangkat Managed Switch: VLAN 802.1Q, Trunk/Access ports, Port Security."""
from __future__ import annotations

import time
from devices.switch import Switch
from networking.vlan import DEFAULT_VLAN, PORT_MODE_ACCESS, PORT_MODE_TRUNK, PortVLANConfig, VLAN


class ManagedSwitch(Switch):
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        super().__init__(device_id, dtype, spec, name, x, y, rotation)
        self.vlans: dict[int, VLAN] = {DEFAULT_VLAN: VLAN(DEFAULT_VLAN, "default")}
        self.port_vlans: dict[str, PortVLANConfig] = {
            p.name: PortVLANConfig() for p in self.ports
        }
        # port_security: {port_name: {"enabled": bool, "max_mac": int, "violation": "protect"|"restrict"|"shutdown", "macs": list[str]}}
        self.port_security: dict[str, dict] = {
            p.name: {"enabled": False, "max_mac": 1, "violation": "shutdown", "macs": []}
            for p in self.ports
        }

    def add_vlan(self, vlan_id: int, name: str = "") -> VLAN:
        v = VLAN(vlan_id, name)
        self.vlans[vlan_id] = v
        return v

    def remove_vlan(self, vlan_id: int) -> bool:
        if vlan_id == DEFAULT_VLAN:
            raise ValueError("VLAN 1 (default) tidak dapat dihapus.")
        if vlan_id in self.vlans:
            del self.vlans[vlan_id]
            # Kembalikan access port di vlan ini ke default
            for pv in self.port_vlans.values():
                if pv.access_vlan == vlan_id:
                    pv.access_vlan = DEFAULT_VLAN
            return True
        return False

    def get_port_vlan(self, port_name: str) -> PortVLANConfig:
        if port_name not in self.port_vlans:
            self.port_vlans[port_name] = PortVLANConfig()
        return self.port_vlans[port_name]

    def set_port_mode(self, port_name: str, mode: str) -> None:
        pv = self.get_port_vlan(port_name)
        pv.mode = mode

    def set_access_vlan(self, port_name: str, vlan_id: int) -> None:
        if vlan_id not in self.vlans:
            self.add_vlan(vlan_id)
        pv = self.get_port_vlan(port_name)
        pv.access_vlan = vlan_id

    def lookup_mac(self, mac: str, vlan_id: int = 1) -> str | None:
        entry = self.mac_table.get(mac.upper())
        if entry:
            if entry["vlan"] == vlan_id:
                return entry["port"]
        return None

    def learn_mac(self, mac: str, port_name: str, vlan_id: int = 1) -> None:
        # Cek port security
        sec = self.port_security.get(port_name)
        if sec and sec["enabled"]:
            mac_u = mac.upper()
            if mac_u not in sec["macs"]:
                if len(sec["macs"]) >= sec["max_mac"]:
                    # Terjadi pelanggaran port security
                    violation = sec["violation"]
                    if violation == "shutdown":
                        port = self.get_port(port_name)
                        port.admin_up = False
                    return
                else:
                    sec["macs"].append(mac_u)
        super().learn_mac(mac, port_name, vlan_id)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["vlans"] = [v.to_dict() for v in self.vlans.values()]
        d["port_vlans"] = {p: pv.to_dict() for p, pv in self.port_vlans.items()}
        d["port_security"] = self.port_security
        return d
