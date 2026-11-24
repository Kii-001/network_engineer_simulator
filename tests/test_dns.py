"""Unit test untuk DNS Server resolution."""
import unittest
from engine.topology_engine import Topology
from engine.dns_engine import DNSEngine
from networking.ip_address import parse_ip


class TestDNS(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.engine = DNSEngine(self.topo)

    def test_a_record_and_cname_resolution(self):
        srv = self.topo.add_device("server", 100, 100, "DNS_SRV")
        srv.dns_service.add_record("server.local", "A", parse_ip("192.168.1.200"))
        srv.dns_service.add_record("intranet.local", "CNAME", "server.local")

        res_a = self.engine.resolve_domain("server.local")
        self.assertEqual(res_a, parse_ip("192.168.1.200"))

        res_cname = self.engine.resolve_domain("intranet.local")
        self.assertEqual(res_cname, parse_ip("192.168.1.200"))

        res_none = self.engine.resolve_domain("notfound.com")
        self.assertIsNone(res_none)


if __name__ == "__main__":
    unittest.main()
