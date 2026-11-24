# NETWORK ENGINEER SIMULATOR (v1.0.0 - Full Release)

Game edukasi simulasi pembangunan dan konfigurasi jaringan komputer profesional dari nol berbasis Python + Pygame.

## Menjalankan (Windows)
```bash
pip install -r requirements.txt
python main.py
```
*(Atau menggunakan environment virtual: `.\venv\Scripts\python.exe main.py`)*

Menjalankan tes unit (100% Pass):
```bash
python -m unittest discover -s tests
```

---

## Status Fase Pengembangan
- [x] **PHASE 1**: Project Setup dan Main Menu
- [x] **PHASE 2**: Game Workspace dan Network Topology Editor
- [x] **PHASE 3**: Device System dan Cable Connection (Straight, Crossover, Fiber, Console)
- [x] **PHASE 4**: IP Addressing dan Subnetting Calculator (VLSM)
- [x] **PHASE 5**: Packet Simulation dan Ping (ICMP, ARP, Animasi Jalur Kabel)
- [x] **PHASE 6**: Router dan Switch Configuration (L2/L3 Processing, Subinterfaces)
- [x] **PHASE 7**: DHCP, DNS, dan VLAN (DORA process, 802.1Q, Trunk/Access)
- [x] **PHASE 8**: Static Routing dan Dynamic Routing (LPM, RIP v2, OSPF v2 SPF Dijkstra)
- [x] **PHASE 9**: CLI Terminal (Cisco IOS parser + Windows Host CMD)
- [x] **PHASE 10**: Firewall dan Network Security (Standard & Extended ACL, Port Security)
- [x] **PHASE 11**: Mission dan Career System (30 Level Progresif, XP, Coins, Stars, Rank)
- [x] **PHASE 12**: Monitoring, Animation, Audio, dan Polish (Packet Monitor, Audio FX, Glowing Pulses)
- [x] **PHASE 13**: Testing, Bug Fixing, dan Packaging (73 Unit Tests Lulus)

---

## Kontrol Workspace & Navigasi
| Aksi | Cara |
|---|---|
| Pasang perangkat | Seret dari sidebar kiri ke kanvas (atau klik item untuk pasang di tengah) |
| Pilih / pindah | Klik / seret perangkat (otomatis snap ke grid 32px) |
| Putar 90 derajat | Tombol `R` atau tombol ROTATE di properties |
| Ganti nama | `F2`, double-click perangkat, atau tombol RENAME |
| Hapus perangkat/kabel | `Del` / `Backspace` atau tombol DELETE |
| Pasang kabel | Tab CABLES di sidebar, atau tombol `1` (Straight), `2` (Crossover), `3` (Fiber), `4` (Console); `V` = kembali ke Select |
| Batal kabel | `Esc` atau klik kanan |
| Lepas kabel | Klik kabel pada mode Select, lalu tekan `Del` atau tombol DISCONNECT |
| Konfigurasi IP GUI | Pilih perangkat, lalu tekan `C` atau tombol CONFIGURE IP |
| Buka CLI Terminal | Pilih perangkat, tekan `T` atau tombol CLI TERMINAL di properties / toolbar |
| Ping Cepat | Pilih perangkat sumber, tekan `P` atau tombol PING |
| Buka Kalkulator Subnet | Tombol `N` atau tombol SUBNET di toolbar |
| Buka Packet Monitor | Tombol PACKETS di toolbar atau klik tab PACKET MONITOR di panel bawah |
| Geser / Pan kanvas | Seret area kosong kanvas, atau klik kanan/tengah mouse |
| Zoom in / out | Scroll mouse, atau tombol `+` / `-` |
| Fit / reset tampilan | Tombol `0` atau tombol FIT di toolbar |
| Grid on/off | Tombol `G` |
| Simpan topologi | `Ctrl+S` atau tombol SAVE di toolbar |

---

## Perintah CLI Terminal Interaktif

### Mode Cisco IOS (Router, Switch, Firewall)
- `enable` / `disable` : Masuk / keluar mode Privileged EXEC (`#`)
- `configure terminal` : Masuk mode Global Configuration (`(config)#`)
- `hostname <nama>` : Mengganti nama perangkat
- `interface <nama>` : Masuk konfigurasi interface (`(config-if)#`)
  - `ip address <ip> <subnet_mask>` : Mengatur IP address port
  - `no shutdown` / `shutdown` : Mengaktifkan / mematikan port
  - `encapsulation dot1Q <vlan_id>` : Mengatur enkapsulasi subinterface (Inter-VLAN)
  - `switchport mode access | trunk` : Mengatur mode port switch
  - `switchport access vlan <vlan_id>` : Menetapkan VLAN access port
  - `switchport port-security [maximum <n>] [violation protect|restrict|shutdown]` : Mengamankan port switch
- `ip route <network> <mask|prefix> <next_hop>` : Menambahkan static route
- `router rip` :
  - `version 2`
  - `network <network_ip>`
- `router ospf <process_id>` :
  - `network <network_ip> <wildcard> area <area_id>`
- `ip dhcp pool <nama_pool>` :
  - `network <network_ip> <mask_ip>`
  - `default-router <gateway_ip>`
  - `dns-server <dns_ip>`
- `access-list <nomor> permit|deny <proto> <src_ip> [src_wildcard]` : Mengatur ACL
- `show ip interface brief` : Melihat status IP dan port
- `show ip route` : Melihat tabel routing (C, S, R, O)
- `show mac address-table` : Melihat tabel MAC switch
- `show vlan brief` : Melihat daftar VLAN switch
- `show running-config` : Melihat konfigurasi aktif
- `ping <ip|domain>` : Mengirim 4 paket ICMP Echo Request
- `traceroute <ip|domain>` : Melacak jalur lompatan hop paket

### Mode Windows Host (PC, Laptop, Server)
- `ipconfig` / `ipconfig /all` : Menampilkan konfigurasi IP, subnet mask, gateway
- `ipconfig /renew` : Meminta alokasi IP baru ke DHCP Server (DORA)
- `ipconfig /release` : Melepaskan alokasi lease DHCP
- `ping <ip|hostname>` : Mengirim tes koneksi ICMP
- `tracert <ip|hostname>` : Melacak rute ke tujuan
- `arp -a` : Menampilkan tabel ARP cache lokal
- `nslookup <domain>` : Menguji resolusi domain ke DNS Server
- `cls` : Membersihkan layar terminal
