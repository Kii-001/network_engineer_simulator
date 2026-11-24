"""Unit test untuk VLAN dan Switching."""
import unittest
from engine.topology_engine import Topology
from engine.switching_engine import SwitchingEngine
from networking.vlan import PORT_MODE_ACCESS, PORT_MODE_TRUNK


class TestVLAN(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.engine = SwitchingEngine(self.topo)

    def test_vlan_access_and_trunk(self):
        sw = self.topo.add_device("managed_switch", 100, 100, "MSW1")
        sw.add_vlan(10, "Sales")
        sw.add_vlan(20, "HR")

        sw.set_port_mode("GigabitEthernet0/1", PORT_MODE_ACCESS)
        sw.set_access_vlan("GigabitEthernet0/1", 10)

        sw.set_port_mode("GigabitEthernet0/2", PORT_MODE_ACCESS)
        sw.set_access_vlan("GigabitEthernet0/2", 20)

        sw.set_port_mode("GigabitEthernet0/12", PORT_MODE_TRUNK)

        # Port 1 (VLAN 10) ke Port 12 (Trunk) harus valid untuk VLAN 10
        self.assertTrue(self.engine.validate_vlan_path(sw.id, "GigabitEthernet0/1", "GigabitEthernet0/12", 10))

        # Port 1 (VLAN 10) ke Port 2 (VLAN 20) harus ditolak untuk isolasi
        self.assertFalse(self.engine.validate_vlan_path(sw.id, "GigabitEthernet0/1", "GigabitEthernet0/2", 10))


if __name__ == "__main__":
    unittest.main()
