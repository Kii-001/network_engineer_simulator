"""Perangkat Server: Layanan DHCP Server, DNS Server, dan Web Server."""
from __future__ import annotations

from devices.base_device import BaseDevice
from networking.arp import ARPTable
from networking.ip_address import ip_to_str, parse_ip


class DHCPServerService:
    def __init__(self) -> None:
        self.enabled: bool = True
        self.pool_name: str = "default_pool"
        self.network: int | None = None
        self.prefix: int | None = None
        self.start_ip: int | None = None
        self.end_ip: int | None = None
        self.default_router: int | None = None
        self.dns_server: int | None = None
        self.lease_time: int = 86400  # detik
        self.leases: dict[str, int] = {}  # {client_mac: assigned_ip}

    def allocate_ip(self, client_mac: str) -> int | None:
        if not self.enabled or self.start_ip is None or self.end_ip is None:
            return None
        # Jika client sudah punya lease
        if client_mac in self.leases:
            return self.leases[client_mac]
        # Alokasikan IP baru yang belum terpakai
        used_ips = set(self.leases.values())
        cur = self.start_ip
        while cur <= self.end_ip:
            if cur not in used_ips:
                self.leases[client_mac] = cur
                return cur
            cur += 1
        return None

    def release_ip(self, client_mac: str) -> bool:
        if client_mac in self.leases:
            del self.leases[client_mac]
            return True
        return False


class DNSServerService:
    def __init__(self) -> None:
        self.enabled: bool = True
        # records: {domain_lowercase: {"type": "A"|"CNAME", "value": ip_int or alias_str}}
        self.records: dict[str, dict] = {}

    def add_record(self, domain: str, rtype: str, value: int | str) -> None:
        self.records[domain.lower().strip()] = {"type": rtype.upper(), "value": value}

    def resolve(self, domain: str) -> int | None:
        if not self.enabled:
            return None
        dom = domain.lower().strip()
        rec = self.records.get(dom)
        if not rec:
            return None
        if rec["type"] == "A":
            return rec["value"]
        elif rec["type"] == "CNAME":
            return self.resolve(rec["value"])
        return None


class Server(BaseDevice):
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        super().__init__(device_id, dtype, spec, name, x, y, rotation)
        self.arp_table = ARPTable()
        self.dhcp_service = DHCPServerService()
        self.dns_service = DNSServerService()

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["dhcp_service"] = {
            "enabled": self.dhcp_service.enabled,
            "network": ip_to_str(self.dhcp_service.network) if self.dhcp_service.network else None,
            "prefix": self.dhcp_service.prefix,
            "start_ip": ip_to_str(self.dhcp_service.start_ip) if self.dhcp_service.start_ip else None,
            "end_ip": ip_to_str(self.dhcp_service.end_ip) if self.dhcp_service.end_ip else None,
            "default_router": ip_to_str(self.dhcp_service.default_router) if self.dhcp_service.default_router else None,
            "dns_server": ip_to_str(self.dhcp_service.dns_server) if self.dhcp_service.dns_server else None,
            "leases": {mac: ip_to_str(ip) for mac, ip in self.dhcp_service.leases.items()}
        }
        d["dns_service"] = {
            "enabled": self.dns_service.enabled,
            "records": {
                dom: {"type": r["type"], "value": ip_to_str(r["value"]) if r["type"] == "A" else r["value"]}
                for dom, r in self.dns_service.records.items()
            }
        }
        return d
