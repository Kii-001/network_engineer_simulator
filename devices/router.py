"""Perangkat Router Layer 3: routing table, subinterfaces, RIP, OSPF, ACL."""
from __future__ import annotations

from devices.base_device import BaseDevice
from networking.arp import ARPTable
from networking.routing import (
    ADMIN_DISTANCES, ROUTE_CONNECTED, ROUTE_OSPF, ROUTE_RIP, ROUTE_STATIC,
    RouteEntry, RoutingTable
)
from networking.ip_address import ip_to_str, parse_ip, parse_mask, prefix_to_mask


class Router(BaseDevice):
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        super().__init__(device_id, dtype, spec, name, x, y, rotation)
        self.routing_table = RoutingTable()
        self.arp_table = ARPTable()
        
        # Subinterfaces untuk Router-on-a-stick (Inter-VLAN Routing)
        # e.g. "GigabitEthernet0/0.10": {"vlan": 10, "ip": 0x..., "prefix": 24, "admin_up": True}
        self.subinterfaces: dict[str, dict] = {}
        
        # Dynamic Routing Configs
        self.rip_enabled: bool = False
        self.rip_version: int = 2
        self.rip_networks: list[int] = []  # Network address
        
        self.ospf_enabled: bool = False
        self.ospf_process_id: int = 1
        self.ospf_networks: list[dict] = []  # [{"network": net, "wildcard": wcard, "area": 0}]

        # ACL & Firewall
        self.acls: dict[int, list[dict]] = {}  # {acl_number: [rules]}
        self.interface_acls: dict[str, dict[str, int]] = {}  # {port: {"in": acl_num, "out": acl_num}}

        self.sync_connected_routes()

    def sync_connected_routes(self) -> None:
        """Sinkronkan rute Connected (C) berdasarkan port dan subinterface yang aktif."""
        # Bersihkan rute connected lama
        self.routing_table.routes = [r for r in self.routing_table.routes if r.protocol != ROUTE_CONNECTED]
        
        # Port fisik
        for p in self.ports:
            if p.admin_up and p.ip is not None and p.prefix is not None:
                mask = prefix_to_mask(p.prefix)
                net = p.ip & mask
                self.routing_table.add_route(RouteEntry(
                    network=net,
                    prefix=p.prefix,
                    next_hop=None,
                    interface=p.name,
                    protocol=ROUTE_CONNECTED,
                    metric=0,
                    admin_distance=0,
                ))

        # Subinterfaces
        for sub_name, sub in self.subinterfaces.items():
            if sub.get("admin_up", True) and sub.get("ip") is not None and sub.get("prefix") is not None:
                mask = prefix_to_mask(sub["prefix"])
                net = sub["ip"] & mask
                self.routing_table.add_route(RouteEntry(
                    network=net,
                    prefix=sub["prefix"],
                    next_hop=None,
                    interface=sub_name,
                    protocol=ROUTE_CONNECTED,
                    metric=0,
                    admin_distance=0,
                ))

    def add_static_route(self, network: int, prefix: int, next_hop: int | None = None, interface: str = "") -> None:
        route = RouteEntry(
            network=network,
            prefix=prefix,
            next_hop=next_hop,
            interface=interface,
            protocol=ROUTE_STATIC,
            metric=1,
            admin_distance=1,
        )
        self.routing_table.add_route(route)

    def remove_static_route(self, network: int, prefix: int, next_hop: int | None = None) -> bool:
        return self.routing_table.remove_route(network, prefix, next_hop)

    def add_subinterface(self, name: str, vlan_id: int, ip: int | None = None, prefix: int | None = None) -> None:
        self.subinterfaces[name] = {
            "vlan": vlan_id,
            "ip": ip,
            "prefix": prefix,
            "admin_up": True,
        }
        self.sync_connected_routes()

    def check_acl(self, port_name: str, direction: str, pkt) -> tuple[bool, str]:
        """Periksa paket terhadap Access Control List."""
        port_rules = self.interface_acls.get(port_name, {})
        acl_num = port_rules.get(direction)
        if acl_num is None or acl_num not in self.acls:
            return True, "No ACL"

        rules = self.acls[acl_num]
        for rule in rules:
            action = rule.get("action", "permit")  # permit | deny
            # Check source match
            rule_src = rule.get("src_ip")
            rule_src_wcard = rule.get("src_wildcard", 0)
            if rule_src is not None and pkt.src_ip is not None:
                if (pkt.src_ip & ~rule_src_wcard) != (rule_src & ~rule_src_wcard):
                    continue

            # Check destination match
            rule_dst = rule.get("dst_ip")
            rule_dst_wcard = rule.get("dst_wildcard", 0)
            if rule_dst is not None and pkt.dst_ip is not None:
                if (pkt.dst_ip & ~rule_dst_wcard) != (rule_dst & ~rule_dst_wcard):
                    continue

            # Check protocol match
            rule_proto = rule.get("protocol")
            if rule_proto and rule_proto.upper() != "IP":
                if rule_proto.upper() != pkt.protocol.upper():
                    continue

            # Rule match!
            allowed = (action == "permit")
            return allowed, f"ACL {acl_num} rule {action}"

        # Default implicit deny di akhir ACL
        return False, f"ACL {acl_num} implicit deny"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["routes"] = self.routing_table.to_dict()
        d["subinterfaces"] = {
            name: {
                "vlan": sub["vlan"],
                "ip": ip_to_str(sub["ip"]) if sub["ip"] is not None else None,
                "prefix": sub["prefix"],
                "admin_up": sub.get("admin_up", True)
            }
            for name, sub in self.subinterfaces.items()
        }
        d["rip"] = {"enabled": self.rip_enabled, "version": self.rip_version, "networks": [ip_to_str(n) for n in self.rip_networks]}
        d["ospf"] = {"enabled": self.ospf_enabled, "process_id": self.ospf_process_id, "networks": self.ospf_networks}
        d["acls"] = self.acls
        d["interface_acls"] = self.interface_acls
        return d
