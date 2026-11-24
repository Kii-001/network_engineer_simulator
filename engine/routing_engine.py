"""Mesin Dynamic Routing: Simulasi protokol RIP v2 dan OSPF v2 (SPF Dijkstra)."""
from __future__ import annotations

import heapq
from networking.routing import (
    ADMIN_DISTANCES, ROUTE_CONNECTED, ROUTE_OSPF, ROUTE_RIP, ROUTE_STATIC,
    RouteEntry
)
from networking.subnetting import SubnetInfo
from networking.ip_address import ip_to_str, prefix_to_mask


class RoutingEngine:
    def __init__(self, topology) -> None:
        self.topo = topology

    def get_routers(self) -> list:
        return [d for d in self.topo.devices.values() if d.type in ("router", "firewall")]

    def get_adjacent_routers(self, router_id: int) -> list[tuple[int, str, int]]:
        """Dapatkan router tetangga: [(neighbor_router_id, local_port_name, neighbor_ip)]."""
        r = self.topo.get(router_id)
        neighbors = []
        for p in r.ports:
            if not p.admin_up or p.link_id is None or p.ip is None:
                continue
            other = p.connected_to
            if not other:
                continue
            target_dev = self.topo.get(other[0])
            
            # Jika terhubung langsung ke router lain
            if target_dev.type in ("router", "firewall"):
                target_port = target_dev.get_port(other[1])
                if target_port.ip is not None and target_port.admin_up:
                    neighbors.append((target_dev.id, p.name, target_port.ip))
            # Jika melewati switch
            elif target_dev.type in ("switch", "managed_switch", "hub"):
                # Cari router lain yang terhubung ke switch yang sama pada subnet yang sama
                for other_dev in self.get_routers():
                    if other_dev.id == router_id:
                        continue
                    for op in other_dev.ports:
                        if op.admin_up and op.link_id is not None and op.ip is not None:
                            if op.connected_to and op.connected_to[0] == target_dev.id:
                                # Cek apakah satu subnet
                                if p.prefix is not None and SubnetInfo(p.ip, p.prefix).contains(op.ip):
                                    neighbors.append((other_dev.id, p.name, op.ip))
        return neighbors

    def converge_all(self) -> None:
        """Jalankan konvergensi routing: Connected -> Static -> RIP -> OSPF."""
        routers = self.get_routers()
        for r in routers:
            if hasattr(r, "sync_connected_routes"):
                r.sync_connected_routes()

        self.converge_rip()
        self.converge_ospf()

    def converge_rip(self) -> None:
        """Simulasi pertukaran rute RIP v2 (Distance Vector dengan Bellman-Ford)."""
        rip_routers = [r for r in self.get_routers() if getattr(r, "rip_enabled", False)]
        if not rip_routers:
            return

        # Hapus rute RIP lama
        for r in rip_routers:
            r.routing_table.clear_dynamic(ROUTE_RIP)

        # Lakukan iterasi penyebaran (maksimal 15 hop)
        changed = True
        iterations = 0
        while changed and iterations < 15:
            changed = False
            iterations += 1
            for r in rip_routers:
                neighbors = self.get_adjacent_routers(r.id)
                for nid, local_port, n_ip in neighbors:
                    nr = self.topo.get(nid)
                    if not getattr(nr, "rip_enabled", False):
                        continue

                    # Periksa rute yang diiklankan oleh r ke nr
                    for route in list(r.routing_table.routes):
                        # Filter apakah rute cocok dengan rip_networks
                        if not self._is_network_in_rip(r, route.network):
                            continue

                        new_metric = route.metric + 1
                        if new_metric >= 16:
                            continue  # Infinity / Unreachable

                        # Cek apakah nr sudah punya rute ini
                        existing = nr.routing_table.lookup(route.network)
                        if existing is None or (existing.protocol == ROUTE_RIP and new_metric < existing.metric):
                            nr.routing_table.add_route(RouteEntry(
                                network=route.network,
                                prefix=route.prefix,
                                next_hop=r.get_port(local_port).ip,
                                interface=local_port,
                                protocol=ROUTE_RIP,
                                metric=new_metric,
                                admin_distance=ADMIN_DISTANCES[ROUTE_RIP],
                            ))
                            changed = True

    def _is_network_in_rip(self, router, network: int) -> bool:
        if not router.rip_networks:
            return True
        for net in router.rip_networks:
            if net == network:
                return True
        return False

    def converge_ospf(self) -> None:
        """Simulasi OSPF v2 Link-State menggunakan algoritma Shortest Path First (Dijkstra)."""
        ospf_routers = [r for r in self.get_routers() if getattr(r, "ospf_enabled", False)]
        if not ospf_routers:
            return

        for r in ospf_routers:
            r.routing_table.clear_dynamic(ROUTE_OSPF)

        # Bangun graf topologi antar router OSPF
        # Graph: {router_id: [(neighbor_router_id, cost, local_port, neighbor_ip)]}
        graph: dict[int, list] = {r.id: [] for r in ospf_routers}
        for r in ospf_routers:
            neighbors = self.get_adjacent_routers(r.id)
            for nid, lport, nip in neighbors:
                if nid in graph:
                    cost = 10  # Cost default (FastEthernet/Gigabit)
                    graph[r.id].append((nid, cost, lport, nip))

        # Untuk setiap router OSPF, jalankan Dijkstra untuk menemukan rute terbaik
        for src_router in ospf_routers:
            dist = {r.id: float('inf') for r in ospf_routers}
            dist[src_router.id] = 0
            first_hop = {}  # {dest_router_id: (next_hop_ip, interface_name)}
            pq = [(0, src_router.id)]

            while pq:
                d, u = heapq.heappop(pq)
                if d > dist[u]:
                    continue

                for v, cost, lport, nip in graph.get(u, []):
                    if dist[u] + cost < dist[v]:
                        dist[v] = dist[u] + cost
                        if u == src_router.id:
                            first_hop[v] = (nip, lport)
                        else:
                            first_hop[v] = first_hop[u]
                        heapq.heappush(pq, (dist[v], v))

            # Tambahkan rute ke semua jaringan yang dimiliki router tujuan
            for dest_router in ospf_routers:
                if dest_router.id == src_router.id or dest_router.id not in first_hop:
                    continue
                next_hop_ip, out_iface = first_hop[dest_router.id]
                total_cost = int(dist[dest_router.id])

                for p in dest_router.ports:
                    if p.admin_up and p.ip is not None and p.prefix is not None:
                        mask = prefix_to_mask(p.prefix)
                        net = p.ip & mask
                        # Jangan pasang jika sudah connected langsung pada src_router
                        if not any(r.network == net and r.protocol == ROUTE_CONNECTED for r in src_router.routing_table.routes):
                            src_router.routing_table.add_route(RouteEntry(
                                network=net,
                                prefix=p.prefix,
                                next_hop=next_hop_ip,
                                interface=out_iface,
                                protocol=ROUTE_OSPF,
                                metric=total_cost,
                                admin_distance=ADMIN_DISTANCES[ROUTE_OSPF],
                            ))
