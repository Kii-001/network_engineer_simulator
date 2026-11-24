"""Unit test untuk MissionManager dan 30 Level Misi."""
import unittest
from engine.topology_engine import Topology
from missions.mission_manager import MissionManager


class TestMissions(unittest.TestCase):
    def setUp(self):
        self.mgr = MissionManager()

    def test_all_30_missions_loaded(self):
        self.assertEqual(len(self.mgr.missions), 30)
        for i in range(1, 31):
            m = self.mgr.get_mission(i)
            self.assertEqual(m["id"], i)
            self.assertIn("title", m)
            self.assertIn("objectives", m)
            self.assertIn("budget", m)

    def test_evaluate_level_1_success(self):
        topo = Topology()
        sw = topo.add_device("switch", 200, 100, "SW1")
        pc1 = topo.add_device("pc", 100, 100, "PC1")
        pc2 = topo.add_device("pc", 300, 100, "PC2")
        topo.connect(pc1.id, "FastEthernet0", sw.id, "FastEthernet0/1", "straight")
        topo.connect(pc2.id, "FastEthernet0", sw.id, "FastEthernet0/2", "straight")

        res = self.mgr.evaluate_mission(1, topo, elapsed_seconds=60)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["score"], 80)
        self.assertGreaterEqual(res["stars"], 2)


if __name__ == "__main__":
    unittest.main()
