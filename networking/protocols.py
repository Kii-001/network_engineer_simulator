"""Definisi protokol jaringan, konstanta port, tipe paket, dan warna animasi."""
from __future__ import annotations

# Protokol Lapisan Jaringan & Transport
PROTO_ARP = "ARP"
PROTO_ICMP = "ICMP"
PROTO_IPv4 = "IPv4"
PROTO_TCP = "TCP"
PROTO_UDP = "UDP"
PROTO_DHCP = "DHCP"
PROTO_DNS = "DNS"
PROTO_RIP = "RIP"
PROTO_OSPF = "OSPF"
PROTO_HTTP = "HTTP"

# Tipe ICMP
ICMP_ECHO_REQUEST = "ECHO_REQUEST"
ICMP_ECHO_REPLY = "ECHO_REPLY"
ICMP_DEST_UNREACHABLE = "DEST_UNREACHABLE"
ICMP_TIME_EXCEEDED = "TIME_EXCEEDED"

# Tipe ARP
ARP_REQUEST = "REQUEST"
ARP_REPLY = "REPLY"

# Tipe DHCP
DHCP_DISCOVER = "DISCOVER"
DHCP_OFFER = "OFFER"
DHCP_REQUEST = "REQUEST"
DHCP_ACK = "ACK"
DHCP_NAK = "NAK"
DHCP_RELEASE = "RELEASE"

# Tipe DNS
DNS_QUERY = "QUERY"
DNS_RESPONSE = "RESPONSE"

# Port Populer
PORT_DNS = 53
PORT_DHCP_SERVER = 67
PORT_DHCP_CLIENT = 68
PORT_HTTP = 80
PORT_HTTPS = 443
PORT_SSH = 22
PORT_TELNET = 23
PORT_RIP = 520

# Broadcast MAC & IP
BROADCAST_MAC = "FF:FF:FF:FF:FF:FF"
BROADCAST_IP = 0xFFFFFFFF  # 255.255.255.255

# Skema warna animasi paket berdasarkan protokol (NOC Theme)
PACKET_COLORS = {
    PROTO_ICMP: (0, 229, 255),       # Cyan
    "ICMP_REPLY": (46, 214, 110),    # Hijau cerah
    PROTO_ARP: (255, 196, 61),       # Kuning
    PROTO_DHCP: (255, 140, 0),       # Oranye
    PROTO_DNS: (186, 104, 200),      # Ungu
    PROTO_TCP: (66, 165, 245),       # Biru
    PROTO_UDP: (100, 181, 246),      # Biru muda
    PROTO_HTTP: (38, 198, 218),      # Teal
    PROTO_RIP: (129, 199, 132),      # Mint
    PROTO_OSPF: (77, 208, 225),      # Light Cyan
    "DROPPED": (240, 66, 76),        # Merah
}
