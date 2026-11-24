import unittest

from core.save_manager import SaveManager
from engine.topology_engine import GRID, Topology, load_catalog, snap


class TestCatalog(unittest.TestCase):
    def test_all_device_types_have_ports_and_cost(self):
        cat = load_catalog()
        self.assertEqual(len(cat), 12)
        for t, spec in cat.items():
            self.assertTrue(spec["ports"], t)
            self.assertGreaterEqual(spec["cost"], 0)


class TestTopology(unittest.TestCase):
    def setUp(self):
        self.t = Topology()

    def test_auto_names_and_reuse(self):
        a = self.t.add_device("router", 0, 0); b = self.t.add_device("router", 96, 0)
        self.assertEqual((a.name, b.name), ("Router1", "Router2"))
        self.t.remove_device(a.id)
        self.assertEqual(self.t.add_device("router", 0, 96).name, "Router1")

    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            self.t.add_device("toaster", 0, 0)

    def test_rename_rules(self):
        a = self.t.add_device("pc", 0, 0); b = self.t.add_device("pc", 96, 0)
        self.assertEqual(self.t.rename_device(a.id, "Kasir-01"), "Kasir-01")
        for bad in ("", "  ", "ada spasi", "x" * 21, "R@uter"):
            with self.assertRaises(ValueError):
                self.t.rename_device(a.id, bad)
        with self.assertRaises(ValueError):   # duplikat (case-insensitive)
            self.t.rename_device(b.id, "kasir-01")
        self.assertEqual(self.t.rename_device(a.id, "Kasir-01"), "Kasir-01")  # nama sendiri boleh

    def test_rotate_wraps(self):
        d = self.t.add_device("server", 0, 0)
        for expected in (90, 180, 270, 0):
            self.assertEqual(self.t.rotate_device(d.id), expected)

    def test_macs_unique(self):
        macs = {self.t.add_device("pc", i * 96, 0).mac for i in range(50)}
        self.assertEqual(len(macs), 50)

    def test_hit_and_occupied(self):
        d = self.t.add_device("hub", 64, 64)
        self.assertIs(self.t.device_at(70, 50), d)
        self.assertIsNone(self.t.device_at(300, 300))
        self.assertTrue(self.t.is_occupied(64, 64))
        self.assertFalse(self.t.is_occupied(64, 64, exclude=d.id))
        x, y = self.t.find_free_spot(64, 64)
        self.assertFalse(self.t.is_occupied(x, y))

    def test_ports_built(self):
        names = [p.name for p in self.t.add_device("switch", 0, 0).ports]
        self.assertEqual(len(names), 8); self.assertEqual(names[0], "FastEthernet0/1")
        r = [p.name for p in self.t.add_device("router", 96, 0).ports]
        self.assertEqual(r, ["GigabitEthernet0/0", "GigabitEthernet0/1", "GigabitEthernet0/2", "GigabitEthernet1/0", "Console"])

    def test_cost_and_counts(self):
        self.t.add_device("router", 0, 0); self.t.add_device("pc", 96, 0); self.t.add_device("pc", 192, 0)
        self.assertEqual(self.t.total_cost(), 150 + 35 + 35)
        self.assertEqual(self.t.counts(), {"router": 1, "pc": 2})

    def test_roundtrip_and_corrupt_data(self):
        self.t.add_device("router", 0, 0); d = self.t.add_device("laptop", 96, 32, name="Bos", rotation=90)
        t2 = Topology.from_dict(self.t.to_dict())
        self.assertEqual([x.to_dict() for x in t2.devices.values()], [x.to_dict() for x in self.t.devices.values()])
        self.assertEqual(t2.add_device("pc", 500, 500).id, d.id + 1)
        bad = {"devices": [{"id": 1, "type": "toaster", "x": 0, "y": 0}, {"id": 2}, {"id": 3, "type": "pc", "x": 1, "y": 1}]}
        self.assertEqual(len(Topology.from_dict(bad).devices), 1)

    def test_snap(self):
        self.assertEqual(snap(47), GRID); self.assertEqual(snap(49), 2 * GRID)


class TestTopologyPersistence(unittest.TestCase):
    def test_save_and_load(self):
        s = SaveManager(":memory:")
        self.assertIsNone(s.load_topology("free_build"))
        t = Topology(); t.add_device("router", 0, 0)
        s.save_topology("free_build", t.to_dict())
        t.add_device("pc", 96, 0)
        s.save_topology("free_build", t.to_dict())  # timpa slot yang sama
        self.assertEqual(len(Topology.from_dict(s.load_topology("free_build")).devices), 2)


if __name__ == "__main__":
    unittest.main()
