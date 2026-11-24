"""Unit test untuk Routing (Static, RIP, OSPF)."""
import unittest
from engine.topology_engine import Topology
from engine.routing_engine import RoutingEngine
from networking.routing import ROUTE_CONNECTED, ROUTE_OSPF, ROUTE_RIP, ROUTE_STATIC, RouteEntry
from networking.ip_address import parse_ip


class TestRouting(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.engine = RoutingEngine(self.topo)

    def test_connected_routes_sync(self):
        r1 = self.topo.add_device("router", 100, 100, "R1")
        self.topo.set_ip(r1.id, "GigabitEthernet0/0", "192.168.1.1", "255.255.255.0")
        self.topo.set_ip(r1.id, "GigabitEthernet0/1", "10.0.0.1", "255.0.0.0")

        self.assertEqual(len(r1.routing_table.routes), 2)
        r = r1.routing_table.lookup(parse_ip("192.168.1.50"))
        self.assertIsNotNone(r)
        self.assertEqual(r.protocol, ROUTE_CONNECTED)
        self.assertEqual(r.interface, "GigabitEthernet0/0")

    def test_longest_prefix_match(self):
        r1 = self.topo.add_device("router", 100, 100, "R1")
        # Default route 0.0.0.0/0
        r1.add_static_route(parse_ip("0.0.0.0"), 0, parse_ip("1.1.1.1"), "Gi0/0")
        # Route 10.0.0.0/8
        r1.add_static_route(parse_ip("10.0.0.0"), 8, parse_ip("2.2.2.2"), "Gi0/1")
        # Route 10.1.0.0/16
        r1.add_static_route(parse_ip("10.1.0.0"), 16, parse_ip("3.3.3.3"), "Gi0/2")

        # 10.1.2.3 harus match ke 10.1.0.0/16 (prefix 16 terpanjang)
        match = r1.routing_table.lookup(parse_ip("10.1.2.3"))
        self.assertIsNotNone(match)
        self.assertEqual(match.prefix, 16)
        self.assertEqual(match.next_hop, parse_ip("3.3.3.3"))

        # 10.5.5.5 harus match ke 10.0.0.0/8 (prefix 8)
        match2 = r1.routing_table.lookup(parse_ip("10.5.5.5"))
        self.assertEqual(match2.prefix, 8)

        # 8.8.8.8 harus match ke default route (prefix 0)
        match3 = r1.routing_table.lookup(parse_ip("8.8.8.8"))
        self.assertEqual(match3.prefix, 0)

    def test_rip_convergence(self):
        r1 = self.topo.add_device("router", 100, 100, "R1")
        r2 = self.topo.add_device("router", 300, 100, "R2")
        self.topo.set_ip(r1.id, "GigabitEthernet0/0", "192.168.1.1", "255.255.255.0")
        self.topo.set_ip(r1.id, "GigabitEthernet0/1", "10.0.0.1", "255.255.255.0")
        self.topo.set_ip(r2.id, "GigabitEthernet0/0", "10.0.0.2", "255.255.255.0")
        self.topo.set_ip(r2.id, "GigabitEthernet0/1", "172.16.1.1", "255.255.255.0")

        self.topo.connect(r1.id, "GigabitEthernet0/1", r2.id, "GigabitEthernet0/0", "crossover")

        r1.rip_enabled = True
        r2.rip_enabled = True
        self.engine.converge_rip()

        # R1 harus mempelajari rute ke 172.16.1.0/24 via R2
        r_learned = r1.routing_table.lookup(parse_ip("172.16.1.100"))
        self.assertIsNotNone(r_learned)
        self.assertEqual(r_learned.protocol, ROUTE_RIP)


if __name__ == "__main__":
    unittest.main()
