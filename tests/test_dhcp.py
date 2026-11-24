"""Unit test untuk DHCP Server & DHCP Client."""
import unittest
from engine.topology_engine import Topology
from engine.dhcp_engine import DHCPEngine
from networking.ip_address import parse_ip


class TestDHCP(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.engine = DHCPEngine(self.topo)

    def test_dhcp_allocation(self):
        srv = self.topo.add_device("server", 100, 100, "SRV")
        pc = self.topo.add_device("pc", 300, 100, "PC1")
        self.topo.connect(srv.id, "GigabitEthernet0/0", pc.id, "FastEthernet0", "crossover")

        srv.dhcp_service.enabled = True
        srv.dhcp_service.network = parse_ip("192.168.10.0")
        srv.dhcp_service.prefix = 24
        srv.dhcp_service.start_ip = parse_ip("192.168.10.50")
        srv.dhcp_service.end_ip = parse_ip("192.168.10.100")
        srv.dhcp_service.default_router = parse_ip("192.168.10.1")
        srv.dhcp_service.dns_server = parse_ip("192.168.10.2")

        res = self.engine.request_dhcp_lease(pc.id)
        self.assertIsNotNone(res)
        self.assertEqual(res["ip"], "192.168.10.50")
        self.assertEqual(res["prefix"], 24)
        self.assertEqual(res["gateway"], "192.168.10.1")
        self.assertEqual(res["dns"], "192.168.10.2")

        # Port PC sekarang memiliki IP
        port = pc.get_port("FastEthernet0")
        self.assertEqual(port.ip, parse_ip("192.168.10.50"))
        self.assertEqual(pc.gateway, parse_ip("192.168.10.1"))
        self.assertEqual(pc.dns_server, parse_ip("192.168.10.2"))

    def test_dhcp_release(self):
        srv = self.topo.add_device("server", 100, 100, "SRV")
        pc = self.topo.add_device("pc", 300, 100, "PC1")
        self.topo.connect(srv.id, "GigabitEthernet0/0", pc.id, "FastEthernet0", "crossover")

        srv.dhcp_service.enabled = True
        srv.dhcp_service.start_ip = parse_ip("192.168.1.100")
        srv.dhcp_service.end_ip = parse_ip("192.168.1.150")

        self.engine.request_dhcp_lease(pc.id)
        self.assertTrue(self.engine.release_dhcp_lease(pc.id))
        self.assertIsNone(pc.get_port("FastEthernet0").ip)
        self.assertNotIn(pc.mac, srv.dhcp_service.leases)


if __name__ == "__main__":
    unittest.main()
