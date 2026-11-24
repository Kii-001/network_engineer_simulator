"""Perangkat Firewall: Filter keamanan jaringan, inspeksi paket, ACL tingkat lanjut."""
from __future__ import annotations

from devices.router import Router


class Firewall(Router):
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        super().__init__(device_id, dtype, spec, name, x, y, rotation)
        self.default_policy: str = "deny"   # 'deny' | 'permit'
        # Aturan firewall stateful: [(id, name, src_net, src_mask, dst_net, dst_mask, proto, port, action)]
        self.firewall_rules: list[dict] = []

    def add_rule(self, name: str, action: str = "permit", proto: str = "IP",
                 src_ip: int | None = None, src_wildcard: int = 0,
                 dst_ip: int | None = None, dst_wildcard: int = 0,
                 port: int | None = None) -> None:
        self.firewall_rules.append({
            "name": name,
            "action": action,
            "proto": proto.upper(),
            "src_ip": src_ip,
            "src_wildcard": src_wildcard,
            "dst_ip": dst_ip,
            "dst_wildcard": dst_wildcard,
            "port": port,
        })

    def check_acl(self, port_name: str, direction: str, pkt) -> tuple[bool, str]:
        # Cek interface ACL router terlebih dahulu
        port_rules = self.interface_acls.get(port_name, {})
        if direction in port_rules:
            return super().check_acl(port_name, direction, pkt)

        # Cek firewall rules umum
        for r in self.firewall_rules:
            if r["proto"] != "IP" and r["proto"] != pkt.protocol.upper():
                continue
            if r["src_ip"] is not None and pkt.src_ip is not None:
                if (pkt.src_ip & ~r["src_wildcard"]) != (r["src_ip"] & ~r["src_wildcard"]):
                    continue
            if r["dst_ip"] is not None and pkt.dst_ip is not None:
                if (pkt.dst_ip & ~r["dst_wildcard"]) != (r["dst_ip"] & ~r["dst_wildcard"]):
                    continue
            allowed = (r["action"] == "permit")
            return allowed, f"Firewall rule '{r['name']}' ({r['action']})"

        # Default policy firewall
        return (self.default_policy == "permit"), f"Firewall default policy ({self.default_policy})"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["default_policy"] = self.default_policy
        d["firewall_rules"] = self.firewall_rules
        return d
