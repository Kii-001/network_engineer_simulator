"""Unit test untuk PacketEngine dan simulasi Ping."""
import unittest
from engine.topology_engine import Topology
from engine.packet_engine import PacketEngine
from networking.protocols import PROTO_ICMP, ICMP_ECHO_REQUEST, ICMP_ECHO_REPLY


class TestPacketEngine(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.engine = PacketEngine(self.topo)

    def test_direct_host_ping(self):
        pc1 = self.topo.add_device("pc", 100, 100, "PC1")
        pc2 = self.topo.add_device("pc", 300, 100, "PC2")
        self.topo.set_ip(pc1.id, "FastEthernet0", "192.168.1.10", "255.255.255.0")
        self.topo.set_ip(pc2.id, "FastEthernet0", "192.168.1.20", "255.255.255.0")
        self.topo.connect(pc1.id, "FastEthernet0", pc2.id, "FastEthernet0", "crossover")

        pkts = self.engine.ping(pc1.id, pc2.get_port("FastEthernet0").ip, count=1)
        self.assertEqual(len(pkts), 1)
        self.assertEqual(pkts[0].protocol, PROTO_ICMP)
        self.assertEqual(pkts[0].status, "in_flight")

        # Simulasi sampai tiba di PC2
        self.engine.update(1.0)
        self.assertEqual(pkts[0].status, "delivered")

        # Balasan ICMP Reply terbentuk
        replies = [p for p in self.engine.active_packets if p.sub_type == ICMP_ECHO_REPLY]
        self.assertEqual(len(replies), 1)

        # Simulasi reply tiba kembali di PC1
        self.engine.update(1.0)
        self.assertEqual(replies[0].status, "delivered")

    def test_switch_flooding_and_mac_learning(self):
        pc1 = self.topo.add_device("pc", 100, 100, "PC1")
        sw = self.topo.add_device("switch", 200, 100, "SW1")
        pc2 = self.topo.add_device("pc", 300, 100, "PC2")
        self.topo.set_ip(pc1.id, "FastEthernet0", "10.0.0.1", "255.255.255.0")
        self.topo.set_ip(pc2.id, "FastEthernet0", "10.0.0.2", "255.255.255.0")
        self.topo.connect(pc1.id, "FastEthernet0", sw.id, "FastEthernet0/1", "straight")
        self.topo.connect(pc2.id, "FastEthernet0", sw.id, "FastEthernet0/2", "straight")

        pkts = self.engine.ping(pc1.id, pc2.get_port("FastEthernet0").ip, count=1)
        self.engine.update(1.0) # Sampai di switch
        # Switch mempelajari MAC PC1
        self.assertIn(pc1.mac.upper(), sw.mac_table)
        self.assertEqual(sw.mac_table[pc1.mac.upper()]["port"], "FastEthernet0/1")

    def test_shutdown_port_drops_packet(self):
        pc1 = self.topo.add_device("pc", 100, 100, "PC1")
        pc2 = self.topo.add_device("pc", 300, 100, "PC2")
        self.topo.set_ip(pc1.id, "FastEthernet0", "192.168.1.10", "255.255.255.0")
        self.topo.set_ip(pc2.id, "FastEthernet0", "192.168.1.20", "255.255.255.0")
        self.topo.connect(pc1.id, "FastEthernet0", pc2.id, "FastEthernet0", "crossover")
        
        # Shutdown port PC1
        pc1.get_port("FastEthernet0").admin_up = False
        pkts = self.engine.ping(pc1.id, pc2.get_port("FastEthernet0").ip, count=1)
        self.assertEqual(len(pkts), 0)


if __name__ == "__main__":
    unittest.main()
