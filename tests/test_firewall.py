"""Unit test untuk Firewall dan ACL."""
import unittest
from engine.topology_engine import Topology
from engine.firewall_engine import FirewallEngine
from networking.ip_address import parse_ip


class TestFirewall(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.engine = FirewallEngine(self.topo)

    def test_acl_evaluation(self):
        rules = [
            {"action": "permit", "protocol": "ICMP", "src_ip": parse_ip("192.168.1.10"), "src_wildcard": 0},
            {"action": "deny", "protocol": "IP", "src_ip": parse_ip("192.168.1.0"), "src_wildcard": parse_ip("0.0.0.255")},
        ]

        # Host 192.168.1.10 ICMP diizinkan oleh rule 1
        allowed, reason = self.engine.evaluate_acl(rules, parse_ip("192.168.1.10"), parse_ip("10.0.0.1"), "ICMP")
        self.assertTrue(allowed)

        # Host 192.168.1.50 ICMP ditolak oleh rule 2
        allowed2, reason2 = self.engine.evaluate_acl(rules, parse_ip("192.168.1.50"), parse_ip("10.0.0.1"), "ICMP")
        self.assertFalse(allowed2)

        # Host di luar subnet ditolak oleh implicit deny
        allowed3, reason3 = self.engine.evaluate_acl(rules, parse_ip("172.16.1.1"), parse_ip("10.0.0.1"), "ICMP")
        self.assertFalse(allowed3)


if __name__ == "__main__":
    unittest.main()
