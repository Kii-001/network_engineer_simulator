"""Master Network Simulation Engine: Mengorkestrasi semua modul simulasi jaringan."""
from __future__ import annotations

from engine.dhcp_engine import DHCPEngine
from engine.dns_engine import DNSEngine
from engine.firewall_engine import FirewallEngine
from engine.packet_engine import PacketEngine
from engine.routing_engine import RoutingEngine
from engine.switching_engine import SwitchingEngine
from engine.topology_engine import Topology


class NetworkSimulationEngine:
    def __init__(self, topology: Topology | None = None) -> None:
        self.topo = topology or Topology()
        self.packets = PacketEngine(self.topo)
        self.switching = SwitchingEngine(self.topo)
        self.routing = RoutingEngine(self.topo)
        self.dhcp = DHCPEngine(self.topo, self.packets)
        self.dns = DNSEngine(self.topo)
        self.firewall = FirewallEngine(self.topo)
        
        self.routing_timer = 0.0
        self.routing_interval = 2.0  # Konvergensi berkala tiap 2 detik

    def update(self, dt: float) -> None:
        # Update simulasi pergerakan dan hop paket data
        self.packets.update(dt)

        # Update dynamic routing periodic
        self.routing_timer += dt
        if self.routing_timer >= self.routing_interval:
            self.routing_timer = 0.0
            self.routing.converge_all()

    def ping(self, src_dev_id: int, dst_ip: int, count: int = 4):
        return self.packets.ping(src_dev_id, dst_ip, count)

    def request_dhcp(self, client_id: int, port_name: str | None = None):
        return self.dhcp.request_dhcp_lease(client_id, port_name)

    def resolve_domain(self, domain: str):
        return self.dns.resolve_domain(domain)
