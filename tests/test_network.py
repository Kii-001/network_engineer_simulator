import unittest

from engine.topology_engine import IPConfigError, Topology


class TestIPConfig(unittest.TestCase):
    def setUp(self):
        self.t = Topology()
        self.pc = self.t.add_device("pc", 0, 0); self.pc2 = self.t.add_device("pc", 96, 0)
        self.r = self.t.add_device("router", 192, 0); self.sw = self.t.add_device("switch", 288, 0)
        self.srv = self.t.add_device("server", 0, 96)

    def test_set_ip_and_gateway(self):
        self.t.set_ip(self.pc.id, "FastEthernet0", "192.168.1.10", "255.255.255.0")
        self.t.set_gateway(self.pc.id, "192.168.1.1")
        p = self.pc.get_port("FastEthernet0")
        self.assertEqual((p.ip, p.prefix), ((192 << 24) | (168 << 16) | (1 << 8) | 10, 24))
        self.assertEqual(self.pc.gateway, (192 << 24) | (168 << 16) | (1 << 8) | 1)

    def test_mask_accepts_cidr_forms(self):
        self.t.set_ip(self.pc.id, "FastEthernet0", "10.0.0.5", "/8"); self.assertEqual(self.pc.get_port("FastEthernet0").prefix, 8)
        self.t.set_ip(self.pc.id, "FastEthernet0", "10.0.0.5", "16"); self.assertEqual(self.pc.get_port("FastEthernet0").prefix, 16)

    def test_rejects_with_field_info(self):
        def err(ip, mask):
            with self.assertRaises(IPConfigError) as cm:
                self.t.set_ip(self.pc.id, "FastEthernet0", ip, mask)
            return cm.exception
        self.assertEqual(err("300.1.1.1", "/24").field, "ip")
        self.assertEqual(err("192.168.1.10", "255.0.255.0").field, "mask")
        self.assertEqual(err("192.168.1.10", "").field, "mask")
        self.assertEqual(err("", "/24").field, "ip")
        for ip in ("192.168.1.0", "192.168.1.255", "127.0.0.1", "224.0.0.1", "0.0.0.0"):
            self.assertEqual(err(ip, "255.255.255.0").field, "ip", ip)
        self.assertIsNone(self.pc.get_port("FastEthernet0").ip)     # tidak ada yang berubah

    def test_ports_without_ip_capability(self):
        with self.assertRaises(IPConfigError): self.t.set_ip(self.pc.id, "RS232", "1.1.1.1", "/24")
        with self.assertRaises(IPConfigError): self.t.set_ip(self.r.id, "Console", "1.1.1.1", "/24")
        with self.assertRaises(IPConfigError): self.t.set_ip(self.sw.id, "FastEthernet0/1", "1.1.1.1", "/24")
        with self.assertRaises(IPConfigError): self.t.set_ip(self.pc.id, "Wireless0", "1.1.1.1", "/24")

    def test_router_overlap_rejected_and_atomic(self):
        self.t.set_ip(self.r.id, "GigabitEthernet0/0", "192.168.1.1", "/24")
        with self.assertRaises(IPConfigError) as cm:
            self.t.set_ip(self.r.id, "GigabitEthernet0/1", "192.168.1.129", "/25")
        self.assertEqual(cm.exception.port, "GigabitEthernet0/1")
        self.t.set_ip(self.r.id, "GigabitEthernet0/1", "192.168.2.1", "/24")   # berbeda subnet OK
        # atomik: satu port valid + satu tidak valid => tidak ada perubahan
        before = [(p.name, p.ip) for p in self.r.ports]
        with self.assertRaises(IPConfigError):
            self.t.apply_ip_config(self.r.id, {"GigabitEthernet0/2": ("10.0.0.1", "/24"), "GigabitEthernet1/0": ("bad", "/24")})
        self.assertEqual(before, [(p.name, p.ip) for p in self.r.ports])

    def test_gateway_rules(self):
        self.t.set_ip(self.pc.id, "FastEthernet0", "192.168.1.10", "/24")
        for bad in ("999.1.1.1", "192.168.1.10", "127.0.0.1", "abc"):
            with self.assertRaises(IPConfigError, msg=bad) as cm:
                self.t.set_gateway(self.pc.id, bad)
            self.assertEqual(cm.exception.field, "gateway")
        with self.assertRaises(IPConfigError): self.t.set_gateway(self.r.id, "192.168.1.1")   # router tanpa gateway
        self.t.set_gateway(self.pc.id, "10.9.9.9")        # di luar subnet tetap boleh (dinilai di Phase 5)
        self.t.set_gateway(self.pc.id, None); self.assertIsNone(self.pc.gateway)

    def test_clear_and_blank(self):
        self.t.set_ip(self.pc.id, "FastEthernet0", "192.168.1.10", "/24")
        self.t.apply_ip_config(self.pc.id, {"FastEthernet0": ("", "")}); self.assertIsNone(self.pc.get_port("FastEthernet0").ip)
        self.t.set_ip(self.pc.id, "FastEthernet0", "192.168.1.10", "/24"); self.t.clear_ip(self.pc.id, "FastEthernet0")
        self.assertIsNone(self.pc.get_port("FastEthernet0").prefix)

    def test_conflicts(self):
        self.assertEqual(self.t.ip_conflicts(), [])
        self.t.set_ip(self.pc.id, "FastEthernet0", "192.168.1.10", "/24")
        self.t.set_ip(self.pc2.id, "FastEthernet0", "192.168.1.10", "/24")
        conf = self.t.ip_conflicts()
        self.assertEqual(len(conf), 1); self.assertEqual(conf[0][0], "192.168.1.10"); self.assertEqual(len(conf[0][1]), 2)

    def test_multi_nic_server_and_roundtrip(self):
        self.t.set_ip(self.srv.id, "GigabitEthernet0/0", "10.0.0.2", "/24"); self.t.set_ip(self.srv.id, "GigabitEthernet0/1", "10.0.1.2", "/24")
        self.t.set_gateway(self.srv.id, "10.0.0.1")
        self.t.set_ip(self.r.id, "GigabitEthernet1/0", "172.16.0.1", "255.255.0.0")
        t2 = Topology.from_dict(self.t.to_dict())
        self.assertEqual(t2.to_dict(), self.t.to_dict())
        self.assertEqual(t2.get(self.srv.id).gateway, self.srv.gateway)

    def test_corrupt_config_is_skipped(self):
        d = self.t.to_dict()
        d["devices"][0]["config"] = {"ports": {"FastEthernet0": ["not-an-ip", "/24"], "Nope": ["1.1.1.1", "/24"]}, "gateway": "xx"}
        t2 = Topology.from_dict(d)
        self.assertEqual(len(t2.devices), len(self.t.devices)); self.assertIsNone(t2.get(self.pc.id).get_port("FastEthernet0").ip)


if __name__ == "__main__":
    unittest.main()
