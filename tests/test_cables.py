import unittest

from engine.topology_engine import Topology
from networking.cables import CableError


class CableTests(unittest.TestCase):
    def setUp(self):
        self.t = Topology()
        self.pc1 = self.t.add_device("pc", 0, 0); self.pc2 = self.t.add_device("pc", 96, 0)
        self.sw = self.t.add_device("switch", 0, 96); self.sw2 = self.t.add_device("switch", 96, 96)
        self.r = self.t.add_device("router", 192, 0); self.msw = self.t.add_device("managed_switch", 192, 96)
        self.r2 = self.t.add_device("router", 288, 0)

    def conn(self, a, pa, b, pb, cable):
        return self.t.connect(a.id, pa, b.id, pb, cable)

    def test_straight_pc_switch_up(self):
        l = self.conn(self.pc1, "FastEthernet0", self.sw, "FastEthernet0/1", "straight")
        self.assertEqual(l.state, "up")
        self.assertEqual(self.pc1.get_port("FastEthernet0").connected_to, (self.sw.id, "FastEthernet0/1"))

    def test_wrong_copper_cable_gives_down_with_reason(self):
        l = self.conn(self.pc1, "FastEthernet0", self.pc2, "FastEthernet0", "straight")
        self.assertEqual(l.state, "down"); self.assertIn("Crossover", l.reason)
        l2 = self.conn(self.sw, "FastEthernet0/1", self.r, "GigabitEthernet0/0", "crossover")
        self.assertEqual(l2.state, "down"); self.assertIn("Straight", l2.reason)

    def test_correct_crossover_cases(self):
        for a, pa, b, pb in ((self.pc1, "FastEthernet0", self.pc2, "FastEthernet0"),
                             (self.sw, "FastEthernet0/1", self.sw2, "FastEthernet0/1"),
                             (self.r, "GigabitEthernet0/0", self.r2, "GigabitEthernet0/0")):
            self.assertEqual(self.conn(a, pa, b, pb, "crossover").state, "up")

    def test_router_switch_straight_router_pc_crossover(self):
        self.assertEqual(self.conn(self.r, "GigabitEthernet0/0", self.sw, "FastEthernet0/2", "straight").state, "up")
        self.assertEqual(self.conn(self.r, "GigabitEthernet0/1", self.pc1, "FastEthernet0", "crossover").state, "up")

    def test_fiber_rules(self):
        self.assertEqual(self.conn(self.msw, "GigabitEthernet1/1", self.r, "GigabitEthernet1/0", "fiber").state, "up")
        with self.assertRaises(CableError):
            self.conn(self.msw, "GigabitEthernet0/1", self.r, "GigabitEthernet0/0", "fiber")
        with self.assertRaises(CableError):   # copper ke port fiber
            self.conn(self.msw, "GigabitEthernet1/2", self.sw, "FastEthernet0/1", "straight")

    def test_console_rules(self):
        l = self.conn(self.pc1, "RS232", self.r, "Console", "console")
        self.assertEqual(l.state, "up")
        with self.assertRaises(CableError):
            self.conn(self.pc2, "FastEthernet0", self.r2, "Console", "console")
        with self.assertRaises(CableError):
            self.conn(self.pc2, "RS232", self.sw, "FastEthernet0/1", "console")

    def test_wireless_and_self_and_unknown_rejected(self):
        lap = self.t.add_device("laptop", 0, 200); ap = self.t.add_device("access_point", 96, 200)
        with self.assertRaises(CableError): self.conn(lap, "Wireless0", ap, "Wireless0", "straight")
        with self.assertRaises(CableError): self.conn(self.sw, "FastEthernet0/1", self.sw, "FastEthernet0/2", "straight")
        with self.assertRaises(CableError): self.conn(self.pc1, "NoPort", self.sw, "FastEthernet0/1", "straight")
        with self.assertRaises(CableError): self.conn(self.pc1, "FastEthernet0", self.sw, "FastEthernet0/1", "laser")

    def test_port_in_use_and_disconnect_frees(self):
        l = self.conn(self.pc1, "FastEthernet0", self.sw, "FastEthernet0/1", "straight")
        with self.assertRaises(CableError):
            self.conn(self.pc2, "FastEthernet0", self.sw, "FastEthernet0/1", "straight")
        self.t.disconnect(l.id)
        self.assertIsNone(self.pc1.get_port("FastEthernet0").link_id)
        self.conn(self.pc2, "FastEthernet0", self.sw, "FastEthernet0/1", "straight")

    def test_remove_device_removes_links(self):
        self.conn(self.pc1, "FastEthernet0", self.sw, "FastEthernet0/1", "straight")
        self.conn(self.pc2, "FastEthernet0", self.sw, "FastEthernet0/2", "straight")
        self.t.remove_device(self.sw.id)
        self.assertEqual(self.t.links, {})
        self.assertIsNone(self.pc1.get_port("FastEthernet0").link_id)

    def test_port_options(self):
        self.conn(self.r, "GigabitEthernet0/0", self.sw, "FastEthernet0/1", "straight")
        opts = {o["name"]: o for o in self.t.port_options(self.r.id, "straight")}
        self.assertFalse(opts["GigabitEthernet0/0"]["enabled"]); self.assertEqual(opts["GigabitEthernet0/0"]["note"], "terpakai")
        self.assertTrue(opts["GigabitEthernet0/1"]["enabled"]); self.assertFalse(opts["Console"]["enabled"])
        fib = {o["name"] for o in self.t.port_options(self.r.id, "fiber") if o["enabled"]}
        self.assertEqual(fib, {"GigabitEthernet1/0"})
        con = {o["name"] for o in self.t.port_options(self.pc1.id, "console", "CONSOLE") if o["enabled"]}
        self.assertEqual(con, {"RS232"})

    def test_port_state_and_refresh(self):
        l = self.conn(self.pc1, "FastEthernet0", self.sw, "FastEthernet0/1", "straight")
        self.assertEqual(self.t.port_state(self.pc1.get_port("FastEthernet0")), "up")
        self.assertEqual(self.t.port_state(self.pc2.get_port("FastEthernet0")), "off")
        self.sw.get_port("FastEthernet0/1").admin_up = False
        self.t.refresh_links(); self.assertEqual(l.state, "down"); self.assertIn("shutdown", l.reason)

    def test_roundtrip_and_corrupt_links(self):
        l1 = self.conn(self.pc1, "FastEthernet0", self.sw, "FastEthernet0/1", "straight")
        l2 = self.conn(self.pc2, "FastEthernet0", self.sw, "FastEthernet0/2", "crossover")
        data = self.t.to_dict()
        t2 = Topology.from_dict(data)
        self.assertEqual({(l.id, l.cable, l.state) for l in t2.links.values()}, {(l1.id, "straight", "up"), (l2.id, "crossover", "down")})
        self.assertEqual(t2.get(self.pc1.id).get_port("FastEthernet0").link_id, l1.id)
        data["links"] += [{"id": 9, "cable": "straight", "a": [999, "x"], "b": [1, "y"]}, {"junk": 1}]
        self.assertEqual(len(Topology.from_dict(data).links), 2)
        self.assertEqual(t2.connect(self.r.id, "GigabitEthernet0/0", self.r2.id, "GigabitEthernet0/0", "crossover").id, max(l1.id, l2.id) + 1)


if __name__ == "__main__":
    unittest.main()
