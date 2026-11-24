"""Mesin simulasi DHCP: Dynamic Host Configuration Protocol (DORA process)."""
from __future__ import annotations

from networking.protocols import (
    BROADCAST_IP, BROADCAST_MAC, DHCP_ACK, DHCP_DISCOVER, DHCP_OFFER,
    DHCP_REQUEST, PROTO_DHCP, PORT_DHCP_CLIENT, PORT_DHCP_SERVER
)
from networking.ip_address import ip_to_str, parse_ip


class DHCPEngine:
    def __init__(self, topology, packet_engine=None) -> None:
        self.topo = topology
        self.pkt_engine = packet_engine

    def find_dhcp_servers(self, client_id: int) -> list:
        """Cari server DHCP yang dapat dijangkau dari client di domain broadcast L2."""
        servers = []
        for dev in self.topo.devices.values():
            if hasattr(dev, "dhcp_service") and dev.dhcp_service.enabled:
                servers.append(dev)
        return servers

    def request_dhcp_lease(self, client_id: int, port_name: str | None = None) -> dict | None:
        """Lakukan proses DORA (Discover, Offer, Request, Ack) secara deterministik."""
        client = self.topo.get(client_id)
        if client.ip_role != "host":
            return None

        ports = [p for p in client.ports if p.kind in ("RJ45", "FIBER")]
        if not ports:
            return None
        target_port = client.get_port(port_name) if port_name else ports[0]

        # Cari DHCP Server terdekat di topologi
        servers = self.find_dhcp_servers(client_id)
        if not servers:
            return None

        # Gunakan server pertama yang memiliki IP pool aktif
        server = servers[0]
        allocated_ip = server.dhcp_service.allocate_ip(client.mac)
        if allocated_ip is None:
            return None

        prefix = server.dhcp_service.prefix or 24
        gateway = server.dhcp_service.default_router
        dns = server.dhcp_service.dns_server

        # Terapkan IP ke port client
        target_port.ip = allocated_ip
        target_port.prefix = prefix
        if gateway is not None:
            client.gateway = gateway
        if dns is not None and hasattr(client, "dns_server"):
            client.dns_server = dns
        if hasattr(client, "dhcp_client"):
            client.dhcp_client = True

        return {
            "ip": ip_to_str(allocated_ip),
            "prefix": prefix,
            "gateway": ip_to_str(gateway) if gateway else None,
            "dns": ip_to_str(dns) if dns else None,
            "server": server.name,
        }

    def release_dhcp_lease(self, client_id: int, port_name: str | None = None) -> bool:
        client = self.topo.get(client_id)
        ports = [p for p in client.ports if p.kind in ("RJ45", "FIBER")]
        if not ports:
            return False
        target_port = client.get_port(port_name) if port_name else ports[0]

        target_port.ip = None
        target_port.prefix = None
        client.gateway = None
        if hasattr(client, "dhcp_client"):
            client.dhcp_client = False

        # Release di server
        for s in self.find_dhcp_servers(client_id):
            s.dhcp_service.release_ip(client.mac)
        return True
