"""Mesin resolusi nama domain (Domain Name System)."""
from __future__ import annotations

from networking.ip_address import ip_to_str


class DNSEngine:
    def __init__(self, topology) -> None:
        self.topo = topology

    def find_dns_servers(self) -> list:
        servers = []
        for dev in self.topo.devices.values():
            if hasattr(dev, "dns_service") and dev.dns_service.enabled:
                servers.append(dev)
        return servers

    def resolve_domain(self, domain: str, dns_server_ip: int | None = None) -> int | None:
        """Resolusi nama domain menjadi IPv4 integer."""
        domain = domain.strip().lower()
        
        # Jika IP server spesifik ditentukan
        if dns_server_ip is not None:
            for s in self.find_dns_servers():
                for p in s.ports:
                    if p.ip == dns_server_ip:
                        res = s.dns_service.resolve(domain)
                        if res is not None:
                            return res

        # Fallback ke semua server DNS yang ada di topologi
        for s in self.find_dns_servers():
            res = s.dns_service.resolve(domain)
            if res is not None:
                return res

        return None
