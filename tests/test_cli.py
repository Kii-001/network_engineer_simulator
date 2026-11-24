"""Unit test untuk InteractiveTerminal (CLI)."""
import unittest
from engine.topology_engine import Topology
from interface.terminal import (
    InteractiveTerminal, MODE_CONFIG, MODE_CONFIG_IF, MODE_PRIV_EXEC, MODE_USER_EXEC
)
from networking.ip_address import ip_to_str, parse_ip


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.topo = Topology()
        self.term = InteractiveTerminal(self.topo)

    def test_ios_mode_transitions_and_ip_config(self):
        r1 = self.topo.add_device("router", 100, 100, "Router1")
        self.term.set_device(r1.id)
        self.assertEqual(self.term.mode, MODE_USER_EXEC)

        self.term.execute_command("enable")
        self.assertEqual(self.term.mode, MODE_PRIV_EXEC)

        self.term.execute_command("configure terminal")
        self.assertEqual(self.term.mode, MODE_CONFIG)

        self.term.execute_command("hostname R1")
        self.assertEqual(r1.name, "R1")

        self.term.execute_command("interface GigabitEthernet0/0")
        self.assertEqual(self.term.mode, MODE_CONFIG_IF)

        self.term.execute_command("ip address 192.168.1.1 255.255.255.0")
        self.assertEqual(r1.get_port("GigabitEthernet0/0").ip, parse_ip("192.168.1.1"))

        self.term.execute_command("no shutdown")
        self.assertTrue(r1.get_port("GigabitEthernet0/0").admin_up)

        self.term.execute_command("exit")
        self.assertEqual(self.term.mode, MODE_CONFIG)

        self.term.execute_command("end")
        self.assertEqual(self.term.mode, MODE_PRIV_EXEC)

    def test_host_ipconfig_command(self):
        pc = self.topo.add_device("pc", 100, 100, "PC1")
        self.topo.set_ip(pc.id, "FastEthernet0", "10.0.0.100", "255.255.255.0")
        self.term.set_device(pc.id)

        self.term.execute_command("ipconfig")
        output_text = "\n".join(t for t, _ in self.term.output_lines)
        self.assertIn("10.0.0.100", output_text)


if __name__ == "__main__":
    unittest.main()
