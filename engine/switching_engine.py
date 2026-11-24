"""Mesin switching Layer 2: VLAN tagging, Trunking, dan Spanning Tree Loop Check."""
from __future__ import annotations


class SwitchingEngine:
    def __init__(self, topology) -> None:
        self.topo = topology

    def validate_vlan_path(self, switch_id: int, in_port: str, out_port: str, vlan_id: int) -> bool:
        """Validasi apakah switch mengizinkan frame dengan vlan_id lewat dari in_port ke out_port."""
        sw = self.topo.get(switch_id)
        if sw.type != "managed_switch" or not hasattr(sw, "get_port_vlan"):
            return True  # Switch unmanaged mengizinkan semua

        in_cfg = sw.get_port_vlan(in_port)
        out_cfg = sw.get_port_vlan(out_port)

        # Cek in_port
        if not in_cfg.is_vlan_allowed(vlan_id):
            return False
        # Cek out_port
        if not out_cfg.is_vlan_allowed(vlan_id):
            return False

        return True

    def detect_l2_loops(self) -> list[list[int]]:
        """Deteksi loop layer 2 sederhana pada topologi switch tanpa STP."""
        # Cari siklus pada perangkat bertipe switch/hub
        adj = {}
        for dev in self.topo.devices.values():
            if dev.type in ("switch", "managed_switch", "hub"):
                adj[dev.id] = []

        for link in self.topo.links.values():
            if link.state != "up":
                continue
            da, db = link.a[0], link.b[0]
            if da in adj and db in adj:
                adj[da].append(db)
                adj[db].append(da)

        cycles = []
        visited = set()

        def dfs(node, parent, path):
            visited.add(node)
            path.append(node)
            for neighbor in adj.get(node, []):
                if neighbor == parent:
                    continue
                if neighbor in path:
                    idx = path.index(neighbor)
                    cycles.append(path[idx:] + [neighbor])
                elif neighbor not in visited:
                    dfs(neighbor, node, path)
            path.pop()

        for node in adj:
            if node not in visited:
                dfs(node, None, [])

        return cycles
