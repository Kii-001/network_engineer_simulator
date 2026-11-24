"""Terminal CLI interaktif: Parser perintah Cisco IOS (Router/Switch) & Windows CMD (PC/Host)."""
from __future__ import annotations

import pygame
from config import COLORS
from interface.widgets import get_font
from networking.ip_address import ip_to_str, mask_to_str, parse_ip, parse_mask, prefix_to_mask
from networking.routing import (
    ADMIN_DISTANCES, ROUTE_CONNECTED, ROUTE_OSPF, ROUTE_RIP, ROUTE_STATIC,
    RouteEntry
)

MODE_USER_EXEC = "user_exec"
MODE_PRIV_EXEC = "priv_exec"
MODE_CONFIG = "config"
MODE_CONFIG_IF = "config_if"
MODE_CONFIG_SUBIF = "config_subif"
MODE_CONFIG_ROUTER = "config_router"
MODE_CONFIG_VLAN = "config_vlan"
MODE_CONFIG_DHCP = "config_dhcp"
MODE_HOST = "host"


class InteractiveTerminal:
    def __init__(self, topology, packet_engine=None, routing_engine=None, dhcp_engine=None, dns_engine=None) -> None:
        self.topo = topology
        self.pkt_engine = packet_engine
        self.routing_engine = routing_engine
        self.dhcp_engine = dhcp_engine
        self.dns_engine = dns_engine

        self.current_device_id: int | None = None
        self.mode = MODE_USER_EXEC
        self.sub_context: dict = {}  # e.g. {"interface": "Gi0/0", "router_proto": "rip", ...}

        self.history: list[str] = []
        self.history_index: int = 0
        self.input_buffer: str = ""
        self.cursor_pos: int = 0

        self.output_lines: list[tuple[str, tuple[int, int, int]]] = []
        self.scroll_offset: int = 0
        self.max_lines: int = 500

        self.cursor_timer: float = 0.0
        self.cursor_visible: bool = True

    def set_device(self, device_id: int) -> None:
        self.current_device_id = device_id
        dev = self.topo.get(device_id)
        self.sub_context.clear()
        if dev.type in ("pc", "laptop", "server", "printer"):
            self.mode = MODE_HOST
            self.output_lines.clear()
            self.print_line(f"Microsoft Windows [Version 10.0.19045.3803]", COLORS["text_dim"])
            self.print_line(f"(c) Microsoft Corporation. All rights reserved.", COLORS["text_dim"])
            self.print_line(f"Connected to local terminal on {dev.name}.", COLORS["cyan"])
            self.print_line("")
        else:
            self.mode = MODE_USER_EXEC
            self.output_lines.clear()
            self.print_line(f"{dev.name} Network Operating System (NES-IOS)", COLORS["cyan"])
            self.print_line("Press ENTER or type 'enable' to enter Privileged EXEC mode.", COLORS["text_dim"])
            self.print_line("")

    def get_prompt(self) -> str:
        if self.current_device_id is None:
            return "NES> "
        dev = self.topo.get(self.current_device_id)
        name = dev.name

        if self.mode == MODE_HOST:
            return f"C:\\Users\\Admin> "
        elif self.mode == MODE_USER_EXEC:
            return f"{name}> "
        elif self.mode == MODE_PRIV_EXEC:
            return f"{name}# "
        elif self.mode == MODE_CONFIG:
            return f"{name}(config)# "
        elif self.mode == MODE_CONFIG_IF:
            iface = self.sub_context.get("interface", "")
            return f"{name}(config-if)# "
        elif self.mode == MODE_CONFIG_SUBIF:
            return f"{name}(config-subif)# "
        elif self.mode == MODE_CONFIG_ROUTER:
            return f"{name}(config-router)# "
        elif self.mode == MODE_CONFIG_VLAN:
            return f"{name}(config-vlan)# "
        elif self.mode == MODE_CONFIG_DHCP:
            return f"{name}(config-dhcp)# "
        return f"{name}# "

    def print_line(self, text: str, color=None) -> None:
        c = color or COLORS["text"]
        for line in text.split("\n"):
            self.output_lines.append((line, c))
        if len(self.output_lines) > self.max_lines:
            self.output_lines = self.output_lines[-self.max_lines:]
        self.scroll_offset = 0

    def execute_command(self, raw_cmd: str) -> None:
        cmd = raw_cmd.strip()
        prompt = self.get_prompt()
        self.print_line(f"{prompt}{raw_cmd}", COLORS["text"])
        if not cmd:
            return

        self.history.append(raw_cmd)
        self.history_index = len(self.history)

        if self.current_device_id is None:
            self.print_line("% Error: Tidak ada perangkat yang dipilih.", COLORS["red"])
            return

        dev = self.topo.get(self.current_device_id)
        if self.mode == MODE_HOST:
            self._handle_host_command(dev, cmd)
        else:
            self._handle_ios_command(dev, cmd)

    def _handle_host_command(self, dev, cmd: str) -> None:
        parts = cmd.split()
        op = parts[0].lower()

        if op == "cls" or op == "clear":
            self.output_lines.clear()

        elif op == "ipconfig":
            self._cmd_host_ipconfig(dev, parts)

        elif op == "ping":
            self._cmd_ping(dev, parts)

        elif op == "traceroute" or op == "tracert":
            self._cmd_traceroute(dev, parts)

        elif op == "arp":
            self._cmd_host_arp(dev, parts)

        elif op == "nslookup":
            self._cmd_host_nslookup(dev, parts)

        elif op == "help":
            self.print_line("Available commands:")
            self.print_line("  ipconfig [/all | /renew | /release]  - Display/refresh IP configuration")
            self.print_line("  ping <ip|hostname>                   - Send ICMP Echo requests")
            self.print_line("  tracert <ip|hostname>                - Trace route to destination")
            self.print_line("  arp -a                               - Display ARP cache")
            self.print_line("  nslookup <hostname>                  - Query DNS name server")
            self.print_line("  cls                                  - Clear screen")

        else:
            self.print_line(f"'{op}' is not recognized as an internal or external command.", COLORS["red"])

    def _cmd_host_ipconfig(self, dev, parts: list[str]) -> None:
        arg = parts[1].lower() if len(parts) > 1 else ""
        if arg == "/renew":
            if self.dhcp_engine:
                res = self.dhcp_engine.request_dhcp_lease(dev.id)
                if res:
                    self.print_line(f"DHCP request successful from {res['server']}:", COLORS["green"])
                    self.print_line(f"   IPv4 Address. . . . . . . . . . . : {res['ip']}")
                    self.print_line(f"   Subnet Mask . . . . . . . . . . . : {mask_to_str(res['prefix'])}")
                    self.print_line(f"   Default Gateway . . . . . . . . . : {res['gateway'] or '0.0.0.0'}")
                    self.print_line(f"   DNS Servers . . . . . . . . . . . : {res['dns'] or 'None'}")
                else:
                    self.print_line("An error occurred while renewing interface: unable to contact DHCP server.", COLORS["red"])
            return

        elif arg == "/release":
            if self.dhcp_engine:
                self.dhcp_engine.release_dhcp_lease(dev.id)
                self.print_line("IP configuration released successfully.", COLORS["yellow"])
            return

        self.print_line("Windows IP Configuration\n")
        for p in dev.ports:
            if p.kind in ("RJ45", "FIBER", "WIRELESS"):
                self.print_line(f"Ethernet adapter {p.name}:")
                if p.link_id is None and p.kind != "WIRELESS":
                    self.print_line("   Media State . . . . . . . . . . . : Media disconnected", COLORS["text_dim"])
                ip_str = ip_to_str(p.ip) if p.ip is not None else "0.0.0.0"
                mask_str = mask_to_str(p.prefix) if p.prefix is not None else "0.0.0.0"
                gw_str = ip_to_str(dev.gateway) if dev.gateway is not None else "0.0.0.0"
                self.print_line(f"   Connection-specific DNS Suffix  . : local")
                self.print_line(f"   Link-local IPv6 Address . . . . . : fe80::{dev.mac.replace(':', '')[:12]}")
                self.print_line(f"   IPv4 Address. . . . . . . . . . . : {ip_str}")
                self.print_line(f"   Subnet Mask . . . . . . . . . . . : {mask_str}")
                self.print_line(f"   Default Gateway . . . . . . . . . : {gw_str}")
                self.print_line("")

    def _cmd_host_arp(self, dev, parts: list[str]) -> None:
        if len(parts) > 1 and parts[1] == "-a":
            self.print_line("Interface: Local Area Connection")
            self.print_line("  Internet Address      Physical Address      Type")
            if hasattr(dev, "arp_table"):
                for entry in dev.arp_table.get_all():
                    self.print_line(f"  {ip_to_str(entry.ip):<20}  {entry.mac:<20}  dynamic")
            self.print_line("")
        else:
            self.print_line("Usage: arp -a")

    def _cmd_host_nslookup(self, dev, parts: list[str]) -> None:
        if len(parts) < 2:
            self.print_line("Usage: nslookup <hostname>")
            return
        target = parts[1]
        dns_ip = getattr(dev, "dns_server", None)
        self.print_line(f"Server:  dns.local")
        self.print_line(f"Address: {ip_to_str(dns_ip) if dns_ip else 'Unknown'}\n")
        if self.dns_engine:
            resolved = self.dns_engine.resolve_domain(target, dns_ip)
            if resolved is not None:
                self.print_line(f"Name:    {target}")
                self.print_line(f"Address: {ip_to_str(resolved)}", COLORS["green"])
            else:
                self.print_line(f"*** Can't find {target}: Non-existent domain", COLORS["red"])

    def _handle_ios_command(self, dev, cmd: str) -> None:
        parts = cmd.split()
        op = parts[0].lower()

        # Global exits
        if op == "exit":
            self._handle_ios_exit()
            return
        elif op == "end":
            self.mode = MODE_PRIV_EXEC
            self.sub_context.clear()
            return
        elif op == "disable":
            self.mode = MODE_USER_EXEC
            return

        # USER EXEC
        if self.mode == MODE_USER_EXEC:
            if op == "enable":
                self.mode = MODE_PRIV_EXEC
            elif op == "ping":
                self._cmd_ping(dev, parts)
            elif op == "traceroute":
                self._cmd_traceroute(dev, parts)
            elif op.startswith("show"):
                self._cmd_ios_show(dev, parts)
            else:
                self.print_line("% Unknown command or incomplete command in User EXEC mode.", COLORS["red"])

        # PRIVILEGED EXEC
        elif self.mode == MODE_PRIV_EXEC:
            if op in ("configure", "conf") and len(parts) > 1 and parts[1].startswith("t"):
                self.mode = MODE_CONFIG
                self.print_line("Enter configuration commands, one per line. End with CNTL/Z or 'end'.")
            elif op.startswith("show"):
                self._cmd_ios_show(dev, parts)
            elif op == "ping":
                self._cmd_ping(dev, parts)
            elif op == "traceroute":
                self._cmd_traceroute(dev, parts)
            elif op == "write" or (op == "copy" and "run" in cmd and "start" in cmd):
                self.print_line("Building configuration...\n[OK]", COLORS["green"])
            else:
                self.print_line("% Invalid input detected at '^' marker.", COLORS["red"])

        # GLOBAL CONFIGURATION
        elif self.mode == MODE_CONFIG:
            self._handle_config_global(dev, parts, cmd)

        # INTERFACE CONFIGURATION
        elif self.mode in (MODE_CONFIG_IF, MODE_CONFIG_SUBIF):
            self._handle_config_interface(dev, parts, cmd)

        # ROUTER CONFIGURATION (RIP / OSPF)
        elif self.mode == MODE_CONFIG_ROUTER:
            self._handle_config_router(dev, parts, cmd)

        # VLAN CONFIGURATION
        elif self.mode == MODE_CONFIG_VLAN:
            self._handle_config_vlan(dev, parts, cmd)

        # DHCP CONFIGURATION
        elif self.mode == MODE_CONFIG_DHCP:
            self._handle_config_dhcp(dev, parts, cmd)

    def _handle_ios_exit(self) -> None:
        if self.mode in (MODE_CONFIG_IF, MODE_CONFIG_SUBIF, MODE_CONFIG_ROUTER, MODE_CONFIG_VLAN, MODE_CONFIG_DHCP):
            self.mode = MODE_CONFIG
            self.sub_context.clear()
        elif self.mode == MODE_CONFIG:
            self.mode = MODE_PRIV_EXEC
        elif self.mode == MODE_PRIV_EXEC:
            self.mode = MODE_USER_EXEC

    def _handle_config_global(self, dev, parts: list[str], cmd: str) -> None:
        op = parts[0].lower()

        if op == "hostname" and len(parts) > 1:
            new_name = parts[1]
            try:
                self.topo.rename_device(dev.id, new_name)
                self.print_line(f"Hostname changed to {dev.name}.", COLORS["green"])
            except ValueError as e:
                self.print_line(f"% {e}", COLORS["red"])

        elif (op in ("interface", "int")) and len(parts) > 1:
            iface_name = parts[1]
            # Cek subinterface mis. Gi0/0.10
            if "." in iface_name and dev.type in ("router", "firewall"):
                self.mode = MODE_CONFIG_SUBIF
                self.sub_context["subinterface"] = iface_name
            else:
                # Normal interface
                # Match port name
                for p in dev.ports:
                    if p.name.lower().startswith(iface_name.lower()) or iface_name.lower() in p.name.lower():
                        self.mode = MODE_CONFIG_IF
                        self.sub_context["interface"] = p.name
                        return
                self.print_line(f"% Invalid interface {iface_name}.", COLORS["red"])

        elif op == "vlan" and len(parts) > 1:
            try:
                vid = int(parts[1])
                if hasattr(dev, "add_vlan"):
                    dev.add_vlan(vid)
                    self.mode = MODE_CONFIG_VLAN
                    self.sub_context["vlan_id"] = vid
                else:
                    self.print_line("% VLAN not supported on this device.", COLORS["red"])
            except ValueError:
                self.print_line("% Invalid VLAN ID.", COLORS["red"])

        elif (op == "ip" and len(parts) > 2 and parts[1] == "route") or (op == "no" and len(parts) > 3 and parts[1] == "ip" and parts[2] == "route"):
            self._handle_ip_route_command(dev, parts)

        elif op == "router" and len(parts) > 1:
            proto = parts[1].lower()
            if proto == "rip":
                dev.rip_enabled = True
                self.mode = MODE_CONFIG_ROUTER
                self.sub_context["router_proto"] = "rip"
            elif proto == "ospf":
                dev.ospf_enabled = True
                pid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
                dev.ospf_process_id = pid
                self.mode = MODE_CONFIG_ROUTER
                self.sub_context["router_proto"] = "ospf"
            else:
                self.print_line("% Protocol not supported. Use 'rip' or 'ospf'.", COLORS["red"])

        elif op == "ip" and len(parts) > 3 and parts[1] == "dhcp" and parts[2] == "pool":
            pool_name = parts[3]
            self.mode = MODE_CONFIG_DHCP
            self.sub_context["dhcp_pool"] = pool_name

        elif op == "access-list" and len(parts) > 3:
            self._handle_access_list_cmd(dev, parts)

        else:
            self.print_line("% Invalid configuration command.", COLORS["red"])

    def _handle_config_interface(self, dev, parts: list[str], cmd: str) -> None:
        op = parts[0].lower()
        iface_name = self.sub_context.get("interface") or self.sub_context.get("subinterface")

        if op == "no" and len(parts) > 1 and parts[1] == "shutdown":
            if iface_name in dev.subinterfaces:
                dev.subinterfaces[iface_name]["admin_up"] = True
            else:
                p = dev.get_port(iface_name)
                p.admin_up = True
            self.topo.refresh_links()
            if hasattr(dev, "sync_connected_routes"):
                dev.sync_connected_routes()
            self.print_line(f"% Interface {iface_name}, changed state to up.", COLORS["green"])

        elif op == "shutdown":
            if iface_name in dev.subinterfaces:
                dev.subinterfaces[iface_name]["admin_up"] = False
            else:
                p = dev.get_port(iface_name)
                p.admin_up = False
            self.topo.refresh_links()
            if hasattr(dev, "sync_connected_routes"):
                dev.sync_connected_routes()
            self.print_line(f"% Interface {iface_name}, changed state to administratively down.", COLORS["yellow"])

        elif op == "ip" and len(parts) > 2 and parts[1] == "address":
            ip_str = parts[2]
            mask_str = parts[3] if len(parts) > 3 else "255.255.255.0"
            try:
                if self.mode == MODE_CONFIG_SUBIF:
                    ip_val = parse_ip(ip_str)
                    prefix_val = parse_mask(mask_str)
                    sub = dev.subinterfaces.get(iface_name, {})
                    sub["ip"] = ip_val
                    sub["prefix"] = prefix_val
                    dev.subinterfaces[iface_name] = sub
                    dev.sync_connected_routes()
                    self.print_line(f"IP address {ip_str}/{prefix_val} set on {iface_name}.", COLORS["green"])
                else:
                    self.topo.set_ip(dev.id, iface_name, ip_str, mask_str)
                    self.print_line(f"IP address {ip_str} set on {iface_name}.", COLORS["green"])
            except Exception as e:
                self.print_line(f"% {e}", COLORS["red"])

        elif op == "encapsulation" and len(parts) > 2 and parts[1].lower() == "dot1q":
            vlan_id = int(parts[2])
            if hasattr(dev, "add_subinterface"):
                dev.add_subinterface(iface_name, vlan_id)
                self.print_line(f"802.1Q encapsulation set to VLAN {vlan_id}.", COLORS["green"])

        elif op == "switchport":
            self._handle_switchport_cmd(dev, iface_name, parts)

        else:
            self.print_line("% Invalid interface command.", COLORS["red"])

    def _handle_switchport_cmd(self, dev, iface_name: str, parts: list[str]) -> None:
        if not hasattr(dev, "set_port_mode"):
            self.print_line("% Switchport commands are only available on switches.", COLORS["red"])
            return

        if len(parts) > 2 and parts[1] == "mode":
            mode = parts[2].lower()
            if mode in ("access", "trunk"):
                dev.set_port_mode(iface_name, mode)
                self.print_line(f"Port {iface_name} mode set to {mode}.", COLORS["green"])

        elif len(parts) > 3 and parts[1] == "access" and parts[2] == "vlan":
            vid = int(parts[3])
            dev.set_access_vlan(iface_name, vid)
            self.print_line(f"Port {iface_name} assigned to VLAN {vid}.", COLORS["green"])

        elif len(parts) > 1 and parts[1] == "port-security":
            sec = dev.port_security.get(iface_name, {})
            sec["enabled"] = True
            if len(parts) > 3 and parts[2] == "maximum":
                sec["max_mac"] = int(parts[3])
            elif len(parts) > 3 and parts[2] == "violation":
                sec["violation"] = parts[3].lower()
            self.print_line(f"Port security enabled on {iface_name}.", COLORS["green"])

    def _handle_config_router(self, dev, parts: list[str], cmd: str) -> None:
        op = parts[0].lower()
        proto = self.sub_context.get("router_proto")

        if op == "network" and len(parts) > 1:
            try:
                net_ip = parse_ip(parts[1])
                if proto == "rip":
                    dev.rip_networks.append(net_ip)
                    self.print_line(f"Network {parts[1]} added to RIP.", COLORS["green"])
                elif proto == "ospf":
                    wcard = parse_ip(parts[2]) if len(parts) > 2 else 0
                    area = int(parts[4]) if len(parts) > 4 and parts[3] == "area" else 0
                    dev.ospf_networks.append({"network": net_ip, "wildcard": wcard, "area": area})
                    self.print_line(f"Network {parts[1]} area {area} added to OSPF.", COLORS["green"])
                if self.routing_engine:
                    self.routing_engine.converge_all()
            except Exception as e:
                self.print_line(f"% {e}", COLORS["red"])

        elif op == "version" and len(parts) > 1 and proto == "rip":
            dev.rip_version = int(parts[1])
            self.print_line(f"RIP version set to {parts[1]}.", COLORS["green"])

    def _handle_config_vlan(self, dev, parts: list[str], cmd: str) -> None:
        op = parts[0].lower()
        vid = self.sub_context.get("vlan_id")
        if op == "name" and len(parts) > 1:
            name = parts[1]
            if vid in dev.vlans:
                dev.vlans[vid].name = name
                self.print_line(f"VLAN {vid} name set to '{name}'.", COLORS["green"])

    def _handle_config_dhcp(self, dev, parts: list[str], cmd: str) -> None:
        op = parts[0].lower()
        if hasattr(dev, "dhcp_service"):
            srv = dev.dhcp_service
            if op == "network" and len(parts) > 2:
                srv.network = parse_ip(parts[1])
                srv.prefix = parse_mask(parts[2])
                srv.start_ip = srv.network + 10
                srv.end_ip = srv.network + 200
                self.print_line(f"DHCP network set to {parts[1]}/{srv.prefix}.", COLORS["green"])
            elif op == "default-router" and len(parts) > 1:
                srv.default_router = parse_ip(parts[1])
                self.print_line(f"DHCP default-router set to {parts[1]}.", COLORS["green"])
            elif op == "dns-server" and len(parts) > 1:
                srv.dns_server = parse_ip(parts[1])
                self.print_line(f"DHCP dns-server set to {parts[1]}.", COLORS["green"])

    def _handle_ip_route_command(self, dev, parts: list[str]) -> None:
        is_no = (parts[0].lower() == "no")
        args = parts[3:] if is_no else parts[2:]
        if len(args) < 3:
            self.print_line("% Incomplete command: ip route <network> <mask> <next_hop>", COLORS["red"])
            return

        try:
            net = parse_ip(args[0])
            mask_val = parse_mask(args[1])
            next_hop = parse_ip(args[2])
            if is_no:
                dev.remove_static_route(net, mask_val, next_hop)
                self.print_line(f"Static route {args[0]}/{mask_val} removed.", COLORS["yellow"])
            else:
                dev.add_static_route(net, mask_val, next_hop)
                self.print_line(f"Static route {args[0]}/{mask_val} via {args[2]} added.", COLORS["green"])
            if self.routing_engine:
                self.routing_engine.converge_all()
        except Exception as e:
            self.print_line(f"% {e}", COLORS["red"])

    def _handle_access_list_cmd(self, dev, parts: list[str]) -> None:
        # access-list <num> permit|deny <proto> <src> [src_wildcard] <dst> [dst_wildcard]
        try:
            num = int(parts[1])
            action = parts[2].lower()
            proto = parts[3].upper() if len(parts) > 3 else "IP"
            src_str = parts[4] if len(parts) > 4 else "any"
            
            src_ip = None if src_str == "any" else parse_ip(src_str)
            src_wcard = 0
            if len(parts) > 5 and parts[5] != "any":
                src_wcard = parse_ip(parts[5])

            rule = {
                "action": action,
                "protocol": proto,
                "src_ip": src_ip,
                "src_wildcard": src_wcard,
            }
            dev.acls.setdefault(num, []).append(rule)
            self.print_line(f"Access-list {num} rule added.", COLORS["green"])
        except Exception as e:
            self.print_line(f"% {e}", COLORS["red"])

    def _cmd_ios_show(self, dev, parts: list[str]) -> None:
        sub = " ".join(parts[1:]).lower()

        if "ip int" in sub or "ip interface brief" in sub:
            self.print_line("Interface                  IP-Address      OK? Method Status                Protocol")
            for p in dev.ports:
                ip_s = ip_to_str(p.ip) if p.ip is not None else "unassigned"
                stat = "up" if p.admin_up else "administratively down"
                proto = "up" if (p.link_id and self.topo.links[p.link_id].state == "up") else "down"
                self.print_line(f"{p.name:<26} {ip_s:<15} YES manual {stat:<21} {proto}")
            for sname, sdata in getattr(dev, "subinterfaces", {}).items():
                ip_s = ip_to_str(sdata.get("ip")) if sdata.get("ip") is not None else "unassigned"
                stat = "up" if sdata.get("admin_up") else "down"
                self.print_line(f"{sname:<26} {ip_s:<15} YES manual {stat:<21} up")

        elif "ip route" in sub:
            self.print_line("Codes: C - connected, S - static, R - RIP, O - OSPF\n")
            if hasattr(dev, "routing_table"):
                for r in dev.routing_table.routes:
                    proto_code = r.protocol
                    net_s = f"{ip_to_str(r.network)}/{r.prefix}"
                    via_s = f"via {ip_to_str(r.next_hop)}" if r.next_hop is not None else f"is directly connected, {r.interface}"
                    self.print_line(f"{proto_code}    {net_s:<18} [{r.admin_distance}/{r.metric}] {via_s}")

        elif "mac" in sub:
            self.print_line("          Mac Address Table")
            self.print_line("-------------------------------------------")
            self.print_line("Vlan    Mac Address       Type        Ports")
            self.print_line("----    -----------       --------    -----")
            if hasattr(dev, "mac_table"):
                for mac, val in dev.mac_table.items():
                    self.print_line(f"{val['vlan']:<7} {mac:<17} DYNAMIC     {val['port']}")

        elif "vlan" in sub:
            self.print_line("VLAN Name                             Status    Ports")
            self.print_line("---- -------------------------------- --------- -------------------------------")
            if hasattr(dev, "vlans"):
                for vid, vlan in dev.vlans.items():
                    ports = [p for p, pv in dev.port_vlans.items() if pv.mode == "access" and pv.access_vlan == vid]
                    p_str = ", ".join(ports)
                    self.print_line(f"{vid:<4} {vlan.name:<32} active    {p_str}")

        elif "running-config" in sub or "run" in sub:
            self.print_line("Building configuration...\n")
            self.print_line(f"hostname {dev.name}!")
            for p in dev.ports:
                self.print_line(f"interface {p.name}")
                if p.ip is not None:
                    self.print_line(f" ip address {ip_to_str(p.ip)} {mask_to_str(p.prefix)}")
                if not p.admin_up:
                    self.print_line(" shutdown")
                self.print_line("!")
            self.print_line("end")

        else:
            self.print_line("% Invalid show command.", COLORS["red"])

    def _cmd_ping(self, dev, parts: list[str]) -> None:
        if len(parts) < 2:
            self.print_line("Usage: ping <destination_ip|hostname>")
            return
        target = parts[1]
        try:
            target_ip = parse_ip(target)
        except Exception:
            # Resolusi nama domain via DNS
            if self.dns_engine:
                target_ip = self.dns_engine.resolve_domain(target)
                if target_ip is None:
                    self.print_line(f"Ping request could not find host {target}.", COLORS["red"])
                    return
            else:
                self.print_line(f"Unknown host {target}.", COLORS["red"])
                return

        self.print_line(f"Sending 4, 32-byte ICMP Echos to {ip_to_str(target_ip)}:")
        if self.pkt_engine:
            pkts = self.pkt_engine.ping(dev.id, target_ip, count=4)
            if not pkts:
                self.print_line("Request timed out. (No active interface with IP/link).", COLORS["red"])
            else:
                self.print_line("Packets in flight... (watch topology canvas)", COLORS["cyan"])

    def _cmd_traceroute(self, dev, parts: list[str]) -> None:
        if len(parts) < 2:
            self.print_line("Usage: traceroute <destination_ip|hostname>")
            return
        target = parts[1]
        try:
            target_ip = parse_ip(target)
        except Exception:
            if self.dns_engine:
                target_ip = self.dns_engine.resolve_domain(target)
                if not target_ip:
                    self.print_line(f"Unable to resolve host {target}.", COLORS["red"])
                    return
            else:
                self.print_line(f"Unknown host {target}.", COLORS["red"])
                return

        self.print_line(f"Tracing route to {ip_to_str(target_ip)} over a maximum of 30 hops:\n")
        # Kirim ping untuk demonstrasi perjalanan
        if self.pkt_engine:
            self.pkt_engine.ping(dev.id, target_ip, count=1)
            self.print_line(f"  1  * * * Packet transmitted along network path.", COLORS["cyan"])

    def handle_event(self, event) -> bool:
        """Penanganan ketikan keyboard terminal."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                cmd = self.input_buffer
                self.input_buffer = ""
                self.cursor_pos = 0
                self.execute_command(cmd)
                return True

            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.input_buffer = self.input_buffer[:self.cursor_pos - 1] + self.input_buffer[self.cursor_pos:]
                    self.cursor_pos -= 1
                return True

            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.input_buffer):
                    self.input_buffer = self.input_buffer[:self.cursor_pos] + self.input_buffer[self.cursor_pos + 1:]
                return True

            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
                return True

            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.input_buffer), self.cursor_pos + 1)
                return True

            elif event.key == pygame.K_UP:
                if self.history and self.history_index > 0:
                    self.history_index -= 1
                    self.input_buffer = self.history[self.history_index]
                    self.cursor_pos = len(self.input_buffer)
                return True

            elif event.key == pygame.K_DOWN:
                if self.history:
                    if self.history_index < len(self.history) - 1:
                        self.history_index += 1
                        self.input_buffer = self.history[self.history_index]
                        self.cursor_pos = len(self.input_buffer)
                    else:
                        self.history_index = len(self.history)
                        self.input_buffer = ""
                        self.cursor_pos = 0
                return True

            elif event.key == pygame.K_PAGEUP:
                self.scroll_offset = min(len(self.output_lines) - 5, self.scroll_offset + 5)
                return True

            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_offset = max(0, self.scroll_offset - 5)
                return True

            elif event.unicode and event.unicode.isprintable():
                self.input_buffer = self.input_buffer[:self.cursor_pos] + event.unicode + self.input_buffer[self.cursor_pos:]
                self.cursor_pos += len(event.unicode)
                return True

        return False

    def update(self, dt: float) -> None:
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

    def draw(self, surface, rect: pygame.Rect) -> None:
        """Render tampilan terminal."""
        pygame.draw.rect(surface, (8, 12, 22), rect)
        pygame.draw.rect(surface, COLORS["blue"], rect, 1)

        font = get_font(13)
        line_h = font.get_linesize()
        visible_lines = max(1, (rect.height - 28) // line_h)

        # Output text rendering (dari bawah ke atas)
        y = rect.bottom - 24
        # Garis prompt & input saat ini
        prompt = self.get_prompt()
        prompt_w, _ = font.size(prompt)
        # Render prompt
        p_surf = font.render(prompt, True, COLORS["cyan"] if self.mode != MODE_HOST else COLORS["text_dim"])
        surface.blit(p_surf, (rect.x + 8, y))

        # Render input buffer
        inp_surf = font.render(self.input_buffer, True, COLORS["text"])
        surface.blit(inp_surf, (rect.x + 8 + prompt_w, y))

        # Cursor
        if self.cursor_visible:
            cursor_x_offset = font.size(self.input_buffer[:self.cursor_pos])[0]
            cx = rect.x + 8 + prompt_w + cursor_x_offset
            pygame.draw.rect(surface, COLORS["cyan"], pygame.Rect(cx, y + 2, 8, line_h - 2))

        # History output
        lines_to_draw = self.output_lines[-visible_lines - self.scroll_offset : len(self.output_lines) - self.scroll_offset]
        y_curr = y - line_h
        for text, col in reversed(lines_to_draw):
            if y_curr < rect.y + 4:
                break
            txt_surf = font.render(text, True, col)
            surface.blit(txt_surf, (rect.x + 8, y_curr))
            y_curr -= line_h
