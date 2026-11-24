"""Mesin simulasi paket data: pembuatan, perjalanan per-hop, animasi, dan diagnosa."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from networking.protocols import (
    BROADCAST_IP, BROADCAST_MAC, ICMP_DEST_UNREACHABLE, ICMP_ECHO_REPLY,
    ICMP_ECHO_REQUEST, ICMP_TIME_EXCEEDED, PACKET_COLORS, PROTO_ARP,
    PROTO_DHCP, PROTO_DNS, PROTO_ICMP, PROTO_TCP, PROTO_UDP,
    ARP_REQUEST, ARP_REPLY
)
from networking.ip_address import ip_to_str


@dataclass
class Packet:
    id: int
    src_dev_id: int
    src_port: str
    src_mac: str
    dst_mac: str
    src_ip: int | None
    dst_ip: int | None
    protocol: str = PROTO_ICMP
    sub_type: str = ICMP_ECHO_REQUEST
    vlan_id: int | None = None
    ttl: int = 64
    payload: dict = field(default_factory=dict)
    
    # Status & History
    status: str = "in_flight"     # 'in_flight' | 'delivered' | 'dropped'
    drop_reason: str | None = None
    hops: list[dict] = field(default_factory=list)
    color: tuple[int, int, int] = field(default_factory=lambda: (0, 229, 255))
    
    # State Animasi Perjalanan
    current_link_id: int | None = None
    progress: float = 0.0         # 0.0 -> 1.0 pada kabel saat ini
    from_dev_id: int = 0
    to_dev_id: int = 0
    speed: float = 1.6            # Kecepatan traversal (hop per detik)
    
    def __post_init__(self):
        if self.sub_type == ICMP_ECHO_REPLY:
            self.color = PACKET_COLORS["ICMP_REPLY"]
        elif self.protocol in PACKET_COLORS:
            self.color = PACKET_COLORS[self.protocol]

    def add_hop(self, dev_name: str, port_name: str, action: str, note: str = "") -> None:
        self.hops.append({
            "device": dev_name,
            "port": port_name,
            "action": action,
            "note": note,
        })

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "src_dev_id": self.src_dev_id,
            "src_mac": self.src_mac,
            "dst_mac": self.dst_mac,
            "src_ip": ip_to_str(self.src_ip) if self.src_ip is not None else None,
            "dst_ip": ip_to_str(self.dst_ip) if self.dst_ip is not None else None,
            "protocol": self.protocol,
            "sub_type": self.sub_type,
            "vlan_id": self.vlan_id,
            "ttl": self.ttl,
            "status": self.status,
            "drop_reason": self.drop_reason,
            "hops": self.hops,
        }


class PacketEngine:
    def __init__(self, topology) -> None:
        self.topo = topology
        self.active_packets: list[Packet] = []
        self.packet_log: list[Packet] = []
        self._next_packet_id = 1
        self.max_log_size = 300
        self.on_packet_delivered = None
        self.on_packet_dropped = None
        self.on_packet_spawned = None

    def create_packet(self, src_dev_id: int, src_port: str, dst_mac: str,
                      src_ip: int | None, dst_ip: int | None,
                      protocol: str = PROTO_ICMP, sub_type: str = ICMP_ECHO_REQUEST,
                      vlan_id: int | None = None, ttl: int = 64, payload: dict | None = None) -> Packet:
        src_dev = self.topo.get(src_dev_id)
        pid = self._next_packet_id
        self._next_packet_id += 1
        
        pkt = Packet(
            id=pid,
            src_dev_id=src_dev_id,
            src_port=src_port,
            src_mac=src_dev.mac,
            dst_mac=dst_mac,
            src_ip=src_ip,
            dst_ip=dst_ip,
            protocol=protocol,
            sub_type=sub_type,
            vlan_id=vlan_id,
            ttl=ttl,
            payload=payload or {},
        )
        pkt.add_hop(src_dev.name, src_port, "CREATE", f"Paket {protocol} dibuat")
        return pkt

    def send_packet(self, pkt: Packet, out_port_name: str) -> bool:
        """Kirim paket keluar melalui port tertentu pada perangkat saat ini."""
        src_dev = self.topo.get(pkt.src_dev_id if pkt.from_dev_id == 0 else pkt.from_dev_id)
        try:
            port = src_dev.get_port(out_port_name)
        except KeyError:
            self._drop_packet(pkt, f"Port '{out_port_name}' tidak ditemukan pada {src_dev.name}.")
            return False

        if not port.admin_up:
            self._drop_packet(pkt, f"Port '{out_port_name}' pada {src_dev.name} dalam kondisi SHUTDOWN.")
            return False

        if port.link_id is None:
            self._drop_packet(pkt, f"Port '{out_port_name}' pada {src_dev.name} tidak terhubung kabel.")
            return False

        link = self.topo.links.get(port.link_id)
        if not link or link.state != "up":
            reason = link.reason if link else "Kabel putus"
            self._drop_packet(pkt, f"Kabel tidak aktif: {reason}")
            return False

        # Tentukan tujuan seberang kabel
        other_end = port.connected_to
        if not other_end:
            self._drop_packet(pkt, "Ujung kabel tidak tersambung.")
            return False

        next_dev_id, next_port_name = other_end
        pkt.current_link_id = port.link_id
        pkt.from_dev_id = src_dev.id
        pkt.to_dev_id = next_dev_id
        pkt.progress = 0.0

        pkt.add_hop(src_dev.name, out_port_name, "TX", f"Mengirim melalui kabel {link.cable}")
        self.active_packets.append(pkt)
        if self.on_packet_spawned:
            self.on_packet_spawned(pkt)
        return True

    def _deliver_packet(self, pkt: Packet, at_dev_id: int, in_port_name: str) -> None:
        pkt.status = "delivered"
        pkt.progress = 1.0
        target_dev = self.topo.get(at_dev_id)
        pkt.add_hop(target_dev.name, in_port_name, "DELIVERED", f"Diterima oleh {target_dev.name}")
        self._archive_packet(pkt)
        if self.on_packet_delivered:
            self.on_packet_delivered(pkt)

        # Respon otomatis jika ICMP Echo Request
        if pkt.protocol == PROTO_ICMP and pkt.sub_type == ICMP_ECHO_REQUEST:
            self._reply_icmp_echo(pkt, target_dev, in_port_name)

    def _drop_packet(self, pkt: Packet, reason: str, at_dev: str = "") -> None:
        pkt.status = "dropped"
        pkt.drop_reason = reason
        dev_name = at_dev or (self.topo.get(pkt.to_dev_id).name if pkt.to_dev_id in self.topo.devices else "Network")
        pkt.add_hop(dev_name, "", "DROPPED", reason)
        self._archive_packet(pkt)
        if self.on_packet_dropped:
            self.on_packet_dropped(pkt, reason)

    def _archive_packet(self, pkt: Packet) -> None:
        if pkt in self.active_packets:
            self.active_packets.remove(pkt)
        self.packet_log.insert(0, pkt)
        if len(self.packet_log) > self.max_log_size:
            self.packet_log.pop()

    def update(self, dt: float) -> None:
        """Update posisi animasi dan simulasi hop per tick."""
        if not self.active_packets:
            return

        for pkt in list(self.active_packets):
            pkt.progress += dt * pkt.speed
            if pkt.progress >= 1.0:
                pkt.progress = 1.0
                self._handle_packet_arrival(pkt)

    def _handle_packet_arrival(self, pkt: Packet) -> None:
        """Dipanggil saat paket tiba di perangkat tujuan kabel (pkt.to_dev_id)."""
        if pkt.to_dev_id not in self.topo.devices:
            self._drop_packet(pkt, "Perangkat tujuan sudah tidak ada.")
            return

        dev = self.topo.get(pkt.to_dev_id)
        link = self.topo.links.get(pkt.current_link_id)
        if not link:
            self._drop_packet(pkt, "Kabel hilang saat transmisi.")
            return

        # Tentukan port masuk pada perangkat tujuan
        in_port_name = link.b[1] if link.b[0] == dev.id else link.a[1]
        try:
            in_port = dev.get_port(in_port_name)
        except KeyError:
            self._drop_packet(pkt, f"Port penerima '{in_port_name}' tidak ditemukan.")
            return

        if not in_port.admin_up:
            self._drop_packet(pkt, f"Port '{in_port_name}' pada {dev.name} mati (shutdown).")
            return

        pkt.add_hop(dev.name, in_port_name, "RX", f"Masuk melalui port {in_port_name}")

        # Delegasikan penanganan paket berdasarkan tipe perangkat
        self._process_device_forwarding(pkt, dev, in_port_name)

    def _process_device_forwarding(self, pkt: Packet, dev, in_port_name: str) -> None:
        """Logika pemrosesan L2 / L3 pada perangkat."""
        dtype = dev.type

        # 1. HUB: Broadcast murni layer 1
        if dtype == "hub":
            out_ports = [p.name for p in dev.ports if p.name != in_port_name and p.link_id is not None]
            if not out_ports:
                self._drop_packet(pkt, f"Tidak ada port lain yang terhubung pada Hub {dev.name}.")
                return
            self.active_packets.remove(pkt)
            for op in out_ports:
                cloned = self._clone_packet(pkt)
                self.send_packet(cloned, op)
            return

        # 2. SWITCH (Unmanaged & Managed)
        if dtype in ("switch", "managed_switch"):
            self._process_switch(pkt, dev, in_port_name)
            return

        # 3. ROUTER / FIREWALL
        if dtype in ("router", "firewall"):
            self._process_router(pkt, dev, in_port_name)
            return

        # 4. END DEVICE / HOST (PC, Laptop, Server, Printer, AP)
        self._process_host(pkt, dev, in_port_name)

    def _process_switch(self, pkt: Packet, dev, in_port_name: str) -> None:
        """Layer 2 Switching: MAC learning, VLAN tagging/checking, dan forwarding."""
        # Update MAC table jika perangkat memiliki mac_table (atau base switch)
        if hasattr(dev, "learn_mac"):
            dev.learn_mac(pkt.src_mac, in_port_name, pkt.vlan_id or 1)

        # Cek VLAN jika managed switch
        if dev.type == "managed_switch" and hasattr(dev, "get_port_vlan"):
            pvlan = dev.get_port_vlan(in_port_name)
            if pvlan.mode == "access":
                if pkt.vlan_id is None:
                    pkt.vlan_id = pvlan.access_vlan
                elif pkt.vlan_id != pvlan.access_vlan:
                    self._drop_packet(pkt, f"VLAN mismatch pada {dev.name}: paket VLAN {pkt.vlan_id} ditolak di access port VLAN {pvlan.access_vlan}")
                    return
            elif pvlan.mode == "trunk":
                vlan = pkt.vlan_id or pvlan.native_vlan
                if not pvlan.is_vlan_allowed(vlan):
                    self._drop_packet(pkt, f"VLAN {vlan} tidak diizinkan di trunk port {in_port_name}")
                    return

        # Forwarding decision
        # Broadcast atau Unknown Unicast -> Flood
        is_broadcast = (pkt.dst_mac == BROADCAST_MAC)
        target_port = None
        if not is_broadcast and hasattr(dev, "lookup_mac"):
            target_port = dev.lookup_mac(pkt.dst_mac, pkt.vlan_id or 1)

        if target_port and target_port != in_port_name:
            # Unicast terarah
            self.active_packets.remove(pkt)
            pkt.from_dev_id = dev.id
            self.send_packet(pkt, target_port)
        else:
            # Flood ke semua port yang terhubung kecuali in_port
            eligible_ports = []
            for p in dev.ports:
                if p.name == in_port_name or p.link_id is None:
                    continue
                if dev.type == "managed_switch" and hasattr(dev, "get_port_vlan"):
                    pvlan = dev.get_port_vlan(p.name)
                    vlan_check = pkt.vlan_id or 1
                    if not pvlan.is_vlan_allowed(vlan_check):
                        continue
                eligible_ports.append(p.name)

            if not eligible_ports:
                self._drop_packet(pkt, f"Tidak ada port tujuan yang cocok untuk flooding pada switch {dev.name}.")
                return

            self.active_packets.remove(pkt)
            for op in eligible_ports:
                cloned = self._clone_packet(pkt)
                cloned.from_dev_id = dev.id
                self.send_packet(cloned, op)

    def _process_router(self, pkt: Packet, dev, in_port_name: str) -> None:
        """Layer 3 Routing: verifikasi MAC/IP, cek ACL/Firewall, LPM route lookup, dan forward."""
        in_port = dev.get_port(in_port_name)

        # Cek apakah paket ditujukan untuk MAC router atau Broadcast
        if pkt.dst_mac != dev.mac and pkt.dst_mac != BROADCAST_MAC:
            self._drop_packet(pkt, f"MAC tujuan {pkt.dst_mac} bukan milik router {dev.name} ({dev.mac}).")
            return

        # Cek apakah ditujukan untuk interface IP router itu sendiri
        for p in dev.ports:
            if p.ip is not None and p.ip == pkt.dst_ip:
                self._deliver_packet(pkt, dev.id, in_port_name)
                return

        # Cek Firewall / ACL in (jika ada)
        if hasattr(dev, "check_acl"):
            allowed, rule_name = dev.check_acl(in_port_name, "in", pkt)
            if not allowed:
                self._drop_packet(pkt, f"Ditolak oleh Firewall / ACL inbound '{rule_name}' pada {dev.name}.")
                return

        # Forwarding: Cek TTL
        pkt.ttl -= 1
        if pkt.ttl <= 0:
            self._drop_packet(pkt, f"TTL habis (TTL Expired) pada router {dev.name}.")
            return

        # Lookup tabel routing
        route = None
        if hasattr(dev, "routing_table") and dev.routing_table:
            route = dev.routing_table.lookup(pkt.dst_ip)

        if not route:
            # Fallback jika ada IP pada interface yang se-subnet dengan dst_ip
            for p in dev.ports:
                if p.ip is not None and p.prefix is not None:
                    from networking.subnetting import SubnetInfo
                    if SubnetInfo(p.ip, p.prefix).contains(pkt.dst_ip):
                        route_port = p.name
                        break
            else:
                self._drop_packet(pkt, f"Tidak ada rute ke {ip_to_str(pkt.dst_ip)} di tabel routing {dev.name}.")
                return
            next_hop_ip = pkt.dst_ip
            out_port_name = route_port
        else:
            out_port_name = route.interface or in_port_name
            next_hop_ip = route.next_hop if route.next_hop is not None else pkt.dst_ip

        # Cek Firewall / ACL out (jika ada)
        if hasattr(dev, "check_acl"):
            allowed, rule_name = dev.check_acl(out_port_name, "out", pkt)
            if not allowed:
                self._drop_packet(pkt, f"Ditolak oleh Firewall / ACL outbound '{rule_name}' pada {dev.name}.")
                return

        # Resolusi MAC next-hop (ARP)
        target_mac = self._resolve_arp_for(dev, next_hop_ip)
        if not target_mac:
            self._drop_packet(pkt, f"ARP gagal: tidak dapat menemukan MAC address untuk IP {ip_to_str(next_hop_ip)}.")
            return

        # Update layer 2 header
        self.active_packets.remove(pkt)
        pkt.src_mac = dev.mac
        pkt.dst_mac = target_mac
        pkt.from_dev_id = dev.id
        self.send_packet(pkt, out_port_name)

    def _process_host(self, pkt: Packet, dev, in_port_name: str) -> None:
        """Penanganan paket pada end-device / host (PC, Server, Laptop, dll)."""
        in_port = dev.get_port(in_port_name)

        # Cek kecocokan MAC (unicast ke dev atau broadcast)
        if pkt.dst_mac != dev.mac and pkt.dst_mac != BROADCAST_MAC:
            self._drop_packet(pkt, f"MAC tujuan ({pkt.dst_mac}) tidak cocok dengan {dev.name} ({dev.mac}).")
            return

        # Jika paket broadcast ARP Request
        if pkt.protocol == PROTO_ARP and pkt.sub_type == ARP_REQUEST:
            target_ip = pkt.payload.get("target_ip")
            if in_port.ip is not None and in_port.ip == target_ip:
                # Simpan ARP source
                if hasattr(dev, "arp_table"):
                    dev.arp_table.add(pkt.src_ip, pkt.src_mac, in_port_name)
                # Kirim ARP Reply
                reply = self.create_packet(
                    src_dev_id=dev.id,
                    src_port=in_port_name,
                    dst_mac=pkt.src_mac,
                    src_ip=in_port.ip,
                    dst_ip=pkt.src_ip,
                    protocol=PROTO_ARP,
                    sub_type=ARP_REPLY,
                    payload={"target_mac": dev.mac, "target_ip": in_port.ip}
                )
                self.send_packet(reply, in_port_name)
                self._deliver_packet(pkt, dev.id, in_port_name)
                return

        # Cek kecocokan IP
        if pkt.dst_ip is not None and in_port.ip is not None:
            if pkt.dst_ip != in_port.ip and pkt.dst_ip != BROADCAST_IP:
                self._drop_packet(pkt, f"IP tujuan ({ip_to_str(pkt.dst_ip)}) tidak sesuai dengan IP {dev.name} ({ip_to_str(in_port.ip)}).")
                return

        # Paket berhasil sampai ke host tujuan!
        self._deliver_packet(pkt, dev.id, in_port_name)

    def _reply_icmp_echo(self, pkt: Packet, target_dev, in_port_name: str) -> None:
        """Balas ICMP Echo Request dengan ICMP Echo Reply."""
        in_port = target_dev.get_port(in_port_name)
        if in_port.ip is None or pkt.src_ip is None:
            return

        reply = self.create_packet(
            src_dev_id=target_dev.id,
            src_port=in_port_name,
            dst_mac=pkt.src_mac,
            src_ip=in_port.ip,
            dst_ip=pkt.src_ip,
            protocol=PROTO_ICMP,
            sub_type=ICMP_ECHO_REPLY,
            ttl=64,
            payload={"seq": pkt.payload.get("seq", 1), "request_id": pkt.id}
        )
        self.send_packet(reply, in_port_name)

    def _resolve_arp_for(self, src_dev, target_ip: int) -> str | None:
        """Cari MAC address untuk target_ip di topologi."""
        # 1. Cek tabel ARP lokal
        if hasattr(src_dev, "arp_table") and src_dev.arp_table:
            cached = src_dev.arp_table.lookup(target_ip)
            if cached:
                return cached

        # 2. Cari di topologi perangkat pemilik IP tersebut
        for d in self.topo.devices.values():
            for p in d.ports:
                if p.ip == target_ip:
                    # Simpan ke ARP table
                    if hasattr(src_dev, "arp_table") and src_dev.arp_table:
                        src_dev.arp_table.add(target_ip, d.mac)
                    return d.mac
        return None

    def _clone_packet(self, pkt: Packet) -> Packet:
        """Klon paket untuk broadcast / flooding."""
        pid = self._next_packet_id
        self._next_packet_id += 1
        cloned = Packet(
            id=pid,
            src_dev_id=pkt.src_dev_id,
            src_port=pkt.src_port,
            src_mac=pkt.src_mac,
            dst_mac=pkt.dst_mac,
            src_ip=pkt.src_ip,
            dst_ip=pkt.dst_ip,
            protocol=pkt.protocol,
            sub_type=pkt.sub_type,
            vlan_id=pkt.vlan_id,
            ttl=pkt.ttl,
            payload=dict(pkt.payload),
            hops=list(pkt.hops),
            color=pkt.color,
            from_dev_id=pkt.from_dev_id,
            to_dev_id=pkt.to_dev_id,
            speed=pkt.speed,
        )
        return cloned

    def ping(self, src_dev_id: int, dst_ip: int, count: int = 4) -> list[Packet]:
        """Eksekusi ping ICMP Echo Request dari perangkat sumber."""
        src_dev = self.topo.get(src_dev_id)
        ports = [p for p in src_dev.ports if p.ip is not None and p.link_id is not None and p.admin_up]
        if not ports:
            return []

        out_port = ports[0]
        packets = []
        for seq in range(1, count + 1):
            # Tentukan apakah target satu subnet atau butuh gateway
            from networking.subnetting import SubnetInfo
            target_mac = None
            if out_port.prefix is not None and SubnetInfo(out_port.ip, out_port.prefix).contains(dst_ip):
                target_mac = self._resolve_arp_for(src_dev, dst_ip)
            else:
                # Lewat default gateway
                if src_dev.gateway is not None:
                    target_mac = self._resolve_arp_for(src_dev, src_dev.gateway)

            if not target_mac:
                target_mac = BROADCAST_MAC

            pkt = self.create_packet(
                src_dev_id=src_dev_id,
                src_port=out_port.name,
                dst_mac=target_mac,
                src_ip=out_port.ip,
                dst_ip=dst_ip,
                protocol=PROTO_ICMP,
                sub_type=ICMP_ECHO_REQUEST,
                payload={"seq": seq}
            )
            if self.send_packet(pkt, out_port.name):
                packets.append(pkt)
        return packets
