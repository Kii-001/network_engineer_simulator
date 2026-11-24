import ipaddress
import random
import unittest

from networking.ip_address import (IPv4Error, ip_to_str, mask_to_str, parse_ip, parse_mask,
                                   prefix_to_mask, wildcard_to_str)
from networking.subnetting import (SubnetError, SubnetInfo, calculate, host_address_error, ip_class, ip_kind,
                                   overlaps, prefix_for_hosts, same_network, split_subnet, vlsm)


class TestParsing(unittest.TestCase):
    def test_valid_ip_roundtrip(self):
        for s in ("0.0.0.0", "192.168.1.10", "255.255.255.255", "10.0.0.1"):
            self.assertEqual(ip_to_str(parse_ip(s)), s)

    def test_invalid_ip(self):
        for bad in ("", "1.2.3", "1.2.3.4.5", "256.1.1.1", "a.b.c.d", "1..2.3", "01.2.3.4", "1.2.3.-4", " ", "1.2.3.4a"):
            with self.assertRaises(IPv4Error, msg=bad):
                parse_ip(bad)

    def test_mask_forms(self):
        self.assertEqual(parse_mask("255.255.255.0"), 24)
        self.assertEqual(parse_mask("/26"), 26)
        self.assertEqual(parse_mask("16"), 16)
        self.assertEqual(parse_mask("0.0.0.0"), 0)
        self.assertEqual(parse_mask("255.255.255.255"), 32)
        self.assertEqual(mask_to_str(27), "255.255.255.224")
        self.assertEqual(wildcard_to_str(27), "0.0.0.31")

    def test_invalid_masks(self):
        for bad in ("", "255.0.255.0", "255.255.255.1", "/33", "33", "abc", "255.255.256.0", "/-1", "/"):
            with self.assertRaises(IPv4Error, msg=bad):
                parse_mask(bad)

    def test_all_prefixes_match_stdlib(self):
        for p in range(33):
            self.assertEqual(ip_to_str(prefix_to_mask(p)), str(ipaddress.ip_network(f"0.0.0.0/{p}").netmask))
            self.assertEqual(parse_mask(mask_to_str(p)), p)


class TestSubnetInfo(unittest.TestCase):
    def test_known_example(self):
        i = calculate("192.168.1.77", "255.255.255.192")   # /26
        self.assertEqual(ip_to_str(i.network), "192.168.1.64")
        self.assertEqual(ip_to_str(i.broadcast), "192.168.1.127")
        self.assertEqual((ip_to_str(i.first_host), ip_to_str(i.last_host)), ("192.168.1.65", "192.168.1.126"))
        self.assertEqual((i.total_addresses, i.usable_hosts), (64, 62))

    def test_special_prefixes(self):
        self.assertEqual(SubnetInfo(parse_ip("10.0.0.5"), 32).usable_hosts, 1)
        i31 = SubnetInfo(parse_ip("10.0.0.4"), 31)
        self.assertEqual((i31.usable_hosts, ip_to_str(i31.first_host), ip_to_str(i31.last_host)), (2, "10.0.0.4", "10.0.0.5"))
        self.assertEqual(SubnetInfo(0, 0).total_addresses, 2 ** 32)

    def test_random_against_stdlib(self):
        rnd = random.Random(42)
        for _ in range(500):
            ip, p = rnd.getrandbits(32), rnd.randint(0, 32)
            mine = SubnetInfo(ip, p)
            ref = ipaddress.ip_network((ip, p), strict=False)
            self.assertEqual(ip_to_str(mine.network), str(ref.network_address))
            self.assertEqual(ip_to_str(mine.broadcast), str(ref.broadcast_address))
            self.assertEqual(mine.total_addresses, ref.num_addresses)
            self.assertEqual(mine.mask, int(ref.netmask))

    def test_class_and_kind(self):
        self.assertEqual([ip_class(parse_ip(x)) for x in ("10.1.1.1", "172.16.0.1", "192.168.0.1", "224.0.0.1", "250.0.0.1")],
                         ["A", "B", "C", "D (multicast)", "E (reserved)"])
        self.assertEqual(ip_kind(parse_ip("172.31.255.1")), "Private (RFC 1918)")
        self.assertEqual(ip_kind(parse_ip("172.32.0.1")), "Public")
        self.assertEqual(ip_kind(parse_ip("127.0.0.1")), "Loopback")
        self.assertEqual(ip_kind(parse_ip("169.254.1.1")), "Link-local (APIPA)")

    def test_host_address_rules(self):
        h = lambda ip, p: host_address_error(parse_ip(ip), p)
        self.assertIsNone(h("192.168.1.10", 24))
        self.assertIn("NETWORK", h("192.168.1.0", 24)); self.assertIn("BROADCAST", h("192.168.1.255", 24))
        self.assertIsNone(h("192.168.1.0", 23))            # .1.0 pada /23 adalah host valid
        self.assertIn("loopback", h("127.0.0.1", 8)); self.assertIn("multicast", h("224.0.0.5", 24))
        self.assertIn("this network", h("0.0.0.0", 0))
        self.assertIsNone(h("10.0.0.0", 31)); self.assertIsNone(h("10.0.0.1", 32))

    def test_same_network_and_overlap(self):
        self.assertTrue(same_network(parse_ip("192.168.1.10"), parse_ip("192.168.1.200"), 24))
        self.assertFalse(same_network(parse_ip("192.168.1.10"), parse_ip("192.168.2.10"), 24))
        self.assertTrue(overlaps(SubnetInfo(parse_ip("10.0.0.0"), 8), SubnetInfo(parse_ip("10.1.2.0"), 24)))
        self.assertFalse(overlaps(SubnetInfo(parse_ip("10.0.0.0"), 24), SubnetInfo(parse_ip("10.0.1.0"), 24)))


class TestSplitAndVlsm(unittest.TestCase):
    def test_split(self):
        base = calculate("192.168.1.0", "/24")
        count, subs = split_subnet(base, 26)
        self.assertEqual(count, 4)
        self.assertEqual([s.cidr() for s in subs], ["192.168.1.0/26", "192.168.1.64/26", "192.168.1.128/26", "192.168.1.192/26"])
        with self.assertRaises(SubnetError): split_subnet(base, 23)
        with self.assertRaises(SubnetError): split_subnet(base, 33)
        count, subs = split_subnet(calculate("10.0.0.0", "/8"), 24, limit=10)
        self.assertEqual((count, len(subs)), (65536, 10))

    def test_prefix_for_hosts(self):
        cases = {1: 30, 2: 30, 3: 29, 6: 29, 7: 28, 14: 28, 15: 27, 30: 27, 50: 26, 62: 26, 100: 25, 126: 25, 127: 24, 254: 24, 255: 23}
        for hosts, prefix in cases.items():
            self.assertEqual(prefix_for_hosts(hosts), prefix, hosts)
            self.assertGreaterEqual(SubnetInfo(0, prefix).usable_hosts, hosts)
        with self.assertRaises(SubnetError): prefix_for_hosts(0)

    def test_vlsm_classic_example(self):
        out = vlsm(calculate("192.168.10.0", "/24"), [25, 100, 10, 50])
        self.assertEqual([(a.label, a.info.cidr()) for a in out],
                         [("Net2", "192.168.10.0/25"), ("Net4", "192.168.10.128/26"), ("Net1", "192.168.10.192/27"), ("Net3", "192.168.10.224/28")])

    def test_vlsm_no_overlap_and_overflow(self):
        out = vlsm(calculate("10.0.0.0", "/22"), [200, 100, 60, 30, 2, 2, 2])
        for i, a in enumerate(out):
            for b in out[i + 1:]:
                self.assertFalse(overlaps(a.info, b.info))
        with self.assertRaises(SubnetError): vlsm(calculate("192.168.10.0", "/24"), [200, 100])
        with self.assertRaises(SubnetError): vlsm(calculate("192.168.10.0", "/24"), [])


if __name__ == "__main__":
    unittest.main()
