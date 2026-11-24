"""Routing table, route entry, dan algoritma Longest Prefix Match (LPM)."""
from __future__ import annotations

from dataclasses import dataclass
from networking.ip_address import ip_to_str, mask_to_str, parse_ip, parse_mask, prefix_to_mask

ROUTE_CONNECTED = "C"
ROUTE_STATIC = "S"
ROUTE_RIP = "R"
ROUTE_OSPF = "O"

ADMIN_DISTANCES = {
    ROUTE_CONNECTED: 0,
    ROUTE_STATIC: 1,
    ROUTE_OSPF: 110,
    ROUTE_RIP: 120,
}


@dataclass
class RouteEntry:
    network: int
    prefix: int
    next_hop: int | None = None      # IP next-hop jika ada
    interface: str = ""              # Nama port keluar (mis. GigabitEthernet0/0)
    protocol: str = ROUTE_STATIC     # C, S, R, O
    metric: int = 1                  # Hop count untuk RIP, Cost untuk OSPF
    admin_distance: int = 1

    def __post_init__(self):
        mask = prefix_to_mask(self.prefix)
        self.network = self.network & mask
        if not self.admin_distance:
            self.admin_distance = ADMIN_DISTANCES.get(self.protocol, 1)

    def matches(self, ip: int) -> bool:
        mask = prefix_to_mask(self.prefix)
        return (ip & mask) == self.network

    def to_dict(self) -> dict:
        return {
            "network": ip_to_str(self.network),
            "prefix": self.prefix,
            "next_hop": ip_to_str(self.next_hop) if self.next_hop is not None else None,
            "interface": self.interface,
            "protocol": self.protocol,
            "metric": self.metric,
            "admin_distance": self.admin_distance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RouteEntry:
        return cls(
            network=parse_ip(data["network"]),
            prefix=data["prefix"],
            next_hop=parse_ip(data["next_hop"]) if data.get("next_hop") else None,
            interface=data.get("interface", ""),
            protocol=data.get("protocol", ROUTE_STATIC),
            metric=data.get("metric", 1),
            admin_distance=data.get("admin_distance", 1),
        )


class RoutingTable:
    def __init__(self) -> None:
        self.routes: list[RouteEntry] = []

    def add_route(self, route: RouteEntry) -> None:
        # Cek apakah rute persis sama sudah ada
        for i, existing in enumerate(self.routes):
            if existing.network == route.network and existing.prefix == route.prefix:
                # Jika protokol sama atau AD lebih rendah, timpa
                if route.admin_distance <= existing.admin_distance:
                    self.routes[i] = route
                    return
                elif route.protocol == existing.protocol and route.next_hop == existing.next_hop:
                    self.routes[i] = route
                    return
                else:
                    return
        self.routes.append(route)

    def remove_route(self, network: int, prefix: int, next_hop: int | None = None) -> bool:
        mask = prefix_to_mask(prefix)
        net = network & mask
        for i, r in enumerate(self.routes):
            if r.network == net and r.prefix == prefix:
                if next_hop is None or r.next_hop == next_hop:
                    del self.routes[i]
                    return True
        return False

    def lookup(self, dst_ip: int) -> RouteEntry | None:
        """Longest Prefix Match (LPM): pilih rute cocok dengan prefix paling panjang dan AD terendah."""
        matching = [r for r in self.routes if r.matches(dst_ip)]
        if not matching:
            return None
        # Sortir: prefix descending (terpanjang), lalu admin_distance ascending, lalu metric ascending
        matching.sort(key=lambda r: (-r.prefix, r.admin_distance, r.metric))
        return matching[0]

    def clear_dynamic(self, protocol: str | None = None) -> None:
        if protocol:
            self.routes = [r for r in self.routes if r.protocol != protocol]
        else:
            self.routes = [r for r in self.routes if r.protocol in (ROUTE_CONNECTED, ROUTE_STATIC)]

    def to_dict(self) -> list[dict]:
        return [r.to_dict() for r in self.routes]

    def from_dict(self, data: list[dict]) -> None:
        self.routes = [RouteEntry.from_dict(d) for d in data]
