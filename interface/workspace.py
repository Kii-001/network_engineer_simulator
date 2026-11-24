"""Network Workspace: topology editor + koneksi kabel."""
from __future__ import annotations

import math

import pygame

from config import COLORS
from core.scene_manager import Scene
from engine.topology_engine import GRID, Topology, snap
from engine.network_engine import NetworkSimulationEngine
from interface.device_config import DeviceConfigDialog
from interface.port_picker import PortPicker
from interface.subnet_calculator import SubnetCalculatorDialog
from interface.terminal import InteractiveTerminal
from interface.packet_monitor import PacketMonitorPanel
from interface.mission_report import MissionReportScene
from interface.widgets import Button, IconButton, draw_text, fit_text, get_font, wrap_text
from missions.mission_manager import MissionManager
from networking.cables import CABLE_TYPES, CableError
from networking.ip_address import ip_to_str

ICON_WORLD = 64
ZOOM_MIN, ZOOM_MAX = 0.4, 2.5
ITEM_H = 58
LINK_HIT_PX = 9
LOG_COLORS = {"info": COLORS["text"], "ok": COLORS["green"], "warn": COLORS["yellow"], "error": COLORS["red"]}
ALLOWED_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
CABLE_KEYS = list(CABLE_TYPES)
BG = (10, 18, 36)


def lerp(a, b, t): return a + (b - a) * t
def lerp_pt(a, b, t): return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))
def lerp_col(a, b, t): return tuple(int(lerp(a[i], b[i], t)) for i in range(3))


def ease_out_back(t: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def seg_dist(p, a, b) -> float:
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def draw_styled_line(surface, color, p1, p2, width, style, zoom=1.0) -> None:
    if style == "solid":
        pygame.draw.line(surface, color, p1, p2, width)
        return
    dash, gap = (max(6, 12 * zoom), max(4, 8 * zoom)) if style == "dashed" else (max(2, 3 * zoom), max(4, 6 * zoom))
    dist = math.dist(p1, p2)
    if dist < 1:
        return
    ux, uy = (p2[0] - p1[0]) / dist, (p2[1] - p1[1]) / dist
    d = 0.0
    while d < dist:
        e = min(d + dash, dist)
        pygame.draw.line(surface, color, (p1[0] + ux * d, p1[1] + uy * d), (p1[0] + ux * e, p1[1] + uy * e), width)
        d += dash + gap


class WorkspaceScene(Scene):
    SLOT = "free_build"

    def __init__(self, game, title: str = "FREE BUILD MODE", mission_id: int | None = None,
                 initial_topology: dict | None = None, mode_type: str = "free") -> None:
        super().__init__(game)
        self.title = title
        self.mission_id = mission_id
        self.mode_type = mode_type
        self.mission_data = MissionManager().get_mission(mission_id) if mission_id else None
        self.slot = f"{mode_type}_{mission_id}" if mission_id else (f"{mode_type}_slot" if mode_type != "free" else self.SLOT)
        data = game.save.load_topology(self.slot) if mode_type != "troubleshoot" else None
        if data:
            self.topo = Topology.from_dict(data)
        elif initial_topology:
            self.topo = Topology.from_dict(initial_topology)
        else:
            self.topo = Topology()
        self.types = list(self.topo.catalog.keys())
        self.cable_items = ["select"] + CABLE_KEYS
        self.tab = "devices"
        self.tool = "select"                   # 'select' atau kunci kabel
        self.pending: dict | None = None       # ujung pertama kabel
        self.picker: PortPicker | None = None
        self.dialog = None                     # dialog modal (konfigurasi IP / kalkulator subnet)
        self.selected: int | None = None
        self.selected_link: int | None = None
        self.hover_id: int | None = None
        self.hover_link: int | None = None
        self.cam = [0.0, 0.0]
        self.zoom = 1.0
        self.show_grid = True
        self.drag: dict | None = None
        self.palette_scroll = 0
        self.prop_scroll = 0
        self.rename_buf: str | None = None
        self.mouse = (0, 0)
        self.log: list[tuple[str, str, str]] = []
        self._t = 0.0
        self._last_click = (0.0, None)
        self._clear_armed_until = 0.0
        self._icons: dict = {}
        self.spawn: dict[int, float] = {}      # animasi pemasangan perangkat
        self.link_anim: dict[int, float] = {}  # animasi penarikan kabel
        self.effects: list[dict] = []
        self.toolbar: list[Button] = []

        # Master Simulation Engine & UI Tabs
        self.net_engine = NetworkSimulationEngine(self.topo)
        self.terminal = InteractiveTerminal(
            self.topo,
            packet_engine=self.net_engine.packets,
            routing_engine=self.net_engine.routing,
            dhcp_engine=self.net_engine.dhcp,
            dns_engine=self.net_engine.dns,
        )
        self.packet_monitor = PacketMonitorPanel(self.net_engine.packets)
        self.bottom_tab = "log"                # 'log' | 'packets' | 'terminal'
        self.bottom_tab_rects: dict = {}

        # Packet engine hooks
        self.net_engine.packets.on_packet_spawned = lambda p: self.play("packet")
        self.net_engine.packets.on_packet_delivered = lambda p: (self.play("success"), self.log_msg(f"Paket #{p.id} {p.protocol} sukses sampai di tujuan.", "ok"))
        self.net_engine.packets.on_packet_dropped = lambda p, reason: (self.play("failure"), self.log_msg(f"Paket #{p.id} {p.protocol} DROPPED: {reason}", "error"))

        self.prop_buttons = {
            "rename": Button("RENAME", self.start_rename),
            "rotate": Button("ROTATE", self.rotate_selected),
            "config": Button("CONFIGURE IP (C)", self.open_config),
            "terminal": Button("CLI (T)", self.open_terminal),
            "ping": Button("PING (P)", self.open_ping_tool),
            "delete": Button("DELETE (Del)", self.delete_selected),
            "disconnect": Button("DISCONNECT (Del)", self.delete_selected_link),
        }
        self._visible_buttons: list[Button] = []
        self.on_resize(game.screen.get_size())
        if self.topo.devices:
            self.fit_view()
            self.log_msg(f"Topologi tersimpan dimuat: {len(self.topo.devices)} perangkat, {len(self.topo.links)} kabel.", "ok")
        else:
            self.log_msg("Workspace siap. Seret perangkat dari sidebar kiri ke kanvas.", "info")

    # ------------------------------------------------------------ layout
    def on_resize(self, size) -> None:
        w, h = size
        self.top_h = 48
        self.left_w = max(172, min(220, int(w * 0.16)))
        self.right_w = max(200, min(270, int(w * 0.20)))
        self.bottom_h = max(110, min(200, int(h * 0.24)))
        self.rect_top = pygame.Rect(0, 0, w, self.top_h)
        self.rect_left = pygame.Rect(0, self.top_h, self.left_w, h - self.top_h)
        self.rect_right = pygame.Rect(w - self.right_w, self.top_h, self.right_w, h - self.top_h)
        self.rect_canvas = pygame.Rect(self.left_w, self.top_h, w - self.left_w - self.right_w, h - self.top_h - self.bottom_h)
        self.rect_bottom = pygame.Rect(self.left_w, h - self.bottom_h, w - self.left_w - self.right_w, self.bottom_h)
        half = (self.left_w - 12) // 2
        self.tab_rects = {"devices": pygame.Rect(self.rect_left.x + 4, self.rect_left.y + 4, half, 28),
                          "cables": pygame.Rect(self.rect_left.x + 8 + half, self.rect_left.y + 4, half, 28)}
        self._build_toolbar(w)
        self._clamp_palette()
        if self.dialog:
            self.dialog.layout(size)

    def _ico(self, name: str):
        return self.game.assets.image(f"icons/{name}.png", (20, 20)) if name else None

    def _build_toolbar(self, width: int) -> None:
        items = [
            ("MENU", "home", self.exit_workspace),
        ]
        if self.mode_type == "troubleshoot":
            items.append(("RESOLVE", "check", self.evaluate_mission_click))
        elif self.mode_type == "challenge":
            items.append(("SUBMIT TRIAL", "check", self.evaluate_mission_click))
        elif self.mode_type == "exam":
            items.append(("FINISH EXAM", "check", self.evaluate_mission_click))
        elif self.mission_id is not None:
            items.append(("SUBMIT", "check", self.evaluate_mission_click))
        items.extend([
            ("ROTATE", "rotate", self.rotate_selected),
            ("DELETE", "delete", self.delete_any), ("SAVE", "save", self.save_now),
            ("CLEAR", "error", self.clear_click), ("GRID", "fullscreen", self.toggle_grid),
            ("SUBNET", "packet", self.open_subnet_calc),
            ("CLI", "terminal", self.open_terminal),
            ("PACKETS", "ping", self.toggle_packet_monitor),
            ("-", "", lambda: self.zoom_step(-1)), ("+", "", lambda: self.zoom_step(1)), ("FIT", "", self.fit_view),
        ])
        font = get_font(14, True)
        self.toolbar = [IconButton(lbl, cb, self._ico(ic)) for lbl, ic, cb in items]
        def wid(b, labels): return (font.size(b.label)[0] + (30 if b.icon else 0) + 18) if (labels or not b.icon) else 38
        labels = sum(wid(b, True) + 6 for b in self.toolbar) < width * 0.76
        x = 8
        for b in self.toolbar:
            b.show_label = labels
            bw = max(36, wid(b, labels))
            b.rect = pygame.Rect(x, 7, bw, 34)
            x += bw + 6

    # ------------------------------------------------------------ util
    def log_msg(self, text: str, level: str = "info") -> None:
        m, s = divmod(int(self._t), 60)
        self.log.append((f"{m:02d}:{s:02d}", text, level))
        del self.log[:-200]

    def play(self, name: str) -> None:
        self.game.assets.play(name)

    def w2s(self, wx, wy):
        c = self.rect_canvas
        return c.centerx + (wx - self.cam[0]) * self.zoom, c.centery + (wy - self.cam[1]) * self.zoom

    def s2w(self, sx, sy):
        c = self.rect_canvas
        return self.cam[0] + (sx - c.centerx) / self.zoom, self.cam[1] + (sy - c.centery) / self.zoom

    def current_items(self) -> list[str]:
        return self.types if self.tab == "devices" else self.cable_items

    def _clamp_palette(self) -> None:
        visible = self.rect_left.height - 40
        self.palette_scroll = max(0, min(self.palette_scroll, max(0, len(self.current_items()) * ITEM_H - visible)))

    def palette_item_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(self.rect_left.x + 6, self.rect_left.y + 38 + i * ITEM_H - self.palette_scroll,
                           self.rect_left.width - 12, ITEM_H - 6)

    def palette_hit(self, pos) -> str | None:
        if not self.rect_left.collidepoint(pos) or pos[1] < self.rect_left.y + 38:
            return None
        for i, key in enumerate(self.current_items()):
            if self.palette_item_rect(i).collidepoint(pos):
                return key
        return None

    @property
    def sel_dev(self):
        return self.topo.devices.get(self.selected) if self.selected is not None else None

    @property
    def sel_link(self):
        return self.topo.links.get(self.selected_link) if self.selected_link is not None else None

    def select(self, dev_id=None, link_id=None) -> None:
        if (dev_id, link_id) != (self.selected, self.selected_link):
            self.rename_buf = None
            self.prop_scroll = 0
        self.selected, self.selected_link = dev_id, link_id

    def add_effect(self, pos, color, delay=0.0, dur=0.6) -> None:
        self.effects.append({"pos": pos, "t0": self._t + delay, "dur": dur, "color": color})

    # ------------------------------------------------------------ aksi: perangkat
    def place_device(self, dtype: str, wx: float, wy: float) -> None:
        x, y = snap(wx), snap(wy)
        if self.topo.is_occupied(x, y):
            x, y = self.topo.find_free_spot(x, y)
            self.log_msg("Posisi terisi; perangkat ditaruh di titik kosong terdekat.", "warn")
        dev = self.topo.add_device(dtype, x, y)
        self.select(dev.id)
        self.spawn[dev.id] = self._t
        self.add_effect((x, y), COLORS["cyan"])
        self.play("place")
        self.log_msg(f"{dev.label} '{dev.name}' dipasang di ({x // GRID}, {y // GRID}).", "ok")

    def rotate_selected(self) -> None:
        dev = self.sel_dev
        if not dev:
            self.log_msg("Pilih perangkat dulu untuk memutar.", "warn")
            return
        deg = self.topo.rotate_device(dev.id)
        self.play("click")
        self.log_msg(f"'{dev.name}' diputar ke {deg} derajat.")

    def delete_selected(self) -> None:
        dev = self.sel_dev
        if not dev:
            self.log_msg("Pilih perangkat dulu untuk menghapus.", "warn")
            return
        n = len(self.topo.links_of(dev.id))
        self.topo.remove_device(dev.id)
        self.select(None)
        if self.pending and self.pending["dev"] == dev.id:
            self.pending = None
        self.play("disconnect")
        extra = f" ({n} kabel ikut terlepas)" if n else ""
        self.log_msg(f"'{dev.name}' dihapus{extra}.", "warn")

    def delete_selected_link(self) -> None:
        link = self.sel_link
        if not link:
            return
        self.topo.disconnect(link.id)
        self.select(None)
        self.play("disconnect")
        self.log_msg(f"Kabel {CABLE_TYPES[link.cable].label} #{link.id} dilepas.", "warn")

    def delete_any(self) -> None:
        if self.selected_link is not None:
            self.delete_selected_link()
        else:
            self.delete_selected()

    def start_rename(self) -> None:
        dev = self.sel_dev
        if not dev:
            self.log_msg("Pilih perangkat dulu untuk mengganti nama.", "warn")
            return
        self.rename_buf = dev.name

    def commit_rename(self) -> None:
        dev = self.sel_dev
        if not dev or self.rename_buf is None:
            return
        old = dev.name
        try:
            new = self.topo.rename_device(dev.id, self.rename_buf)
        except ValueError as e:
            self.play("error")
            self.log_msg(str(e), "error")
            return
        self.rename_buf = None
        self.play("notification")
        self.log_msg(f"'{old}' diganti menjadi '{new}'.", "ok")

    # ------------------------------------------------------------ aksi: konfigurasi IP
    def open_config(self) -> None:
        dev = self.sel_dev
        if not dev:
            self.log_msg("Pilih perangkat dulu untuk konfigurasi IP.", "warn")
        elif dev.ip_role == "none":
            self.play("error")
            self.log_msg(f"{dev.label} '{dev.name}' adalah perangkat layer 2: tidak punya konfigurasi IP.", "warn")
        else:
            self.pending, self.picker = None, None
            self.dialog = DeviceConfigDialog(self, dev)
            self.play("click")

    def open_subnet_calc(self) -> None:
        self.pending, self.picker = None, None
        self.dialog = SubnetCalculatorDialog(self)
        self.play("click")

    def on_ip_applied(self, dev) -> None:
        from devices.base_device import short_port_name
        from networking.ip_address import ip_to_str
        cfg = [f"{short_port_name(p.name)}={ip_to_str(p.ip)}/{p.prefix}" for p in dev.ip_ports() if p.ip is not None]
        parts = ", ".join(cfg) if cfg else "tanpa IP"
        gw = f"; gateway {ip_to_str(dev.gateway)}" if dev.gateway is not None else ""
        self.play("notification")
        self.log_msg(f"IP {dev.name}: {parts}{gw}.", "ok")
        for ip, owners in self.topo.ip_conflicts():
            if any(n == dev.name for n, _ in owners):
                self.play("error")
                self.log_msg(f"KONFLIK IP {ip}: " + " dan ".join(f"{n}:{short_port_name(pn)}" for n, pn in owners), "warn")

    def open_terminal(self) -> None:
        self.bottom_tab = "terminal"
        if self.sel_dev:
            self.terminal.set_device(self.sel_dev.id)
        elif self.topo.devices:
            first_id = next(iter(self.topo.devices.keys()))
            self.terminal.set_device(first_id)
        self.play("click")
        self.log_msg("Terminal CLI aktif. Ketik perintah pada panel bawah.", "info")

    def toggle_packet_monitor(self) -> None:
        self.bottom_tab = "packets" if self.bottom_tab != "packets" else "log"
        self.play("click")

    def open_ping_tool(self) -> None:
        dev = self.sel_dev
        if not dev:
            self.log_msg("Pilih perangkat sumber terlebih dahulu untuk Ping.", "warn")
            return
        target_ip = dev.gateway
        if target_ip is None:
            for other in self.topo.devices.values():
                if other.id != dev.id:
                    for p in other.ports:
                        if p.ip is not None:
                            target_ip = p.ip
                            break
                    if target_ip is not None:
                        break
        if target_ip is None:
            self.log_msg("Tidak ada target IP atau Gateway yang ditemukan untuk di-ping.", "warn")
            self.play("error")
            return
        self.play("click")
        self.log_msg(f"Mengirim Ping dari {dev.name} ke {ip_to_str(target_ip)}...", "info")
        self.net_engine.ping(dev.id, target_ip, count=4)

    def evaluate_mission_click(self) -> None:
        if self.mode_type == "troubleshoot":
            up_links = [l for l in self.topo.links.values() if l.state == "up"]
            resolved = len(up_links) >= 2
            res = {
                "success": resolved,
                "mission_id": 0,
                "title": self.title,
                "score": 100 if resolved else 50,
                "stars": 3 if resolved else 1,
                "xp": 350,
                "coins": 180,
                "passed_objectives": ["Jaringan berhasil didiagnosa dan dipulihkan ke status UP"],
                "errors": [] if resolved else ["Masih ada interface / kabel yang mengalami gangguan."],
                "elapsed_seconds": self._t
            }
            if resolved:
                self.game.save.add_rewards(res["xp"], res["coins"])
                self.play("level_up")
            else:
                self.play("failure")
            self.game.scenes.push(MissionReportScene(self.game, res))
            return
        elif self.mode_type == "challenge":
            cost = self.topo.total_cost()
            success = len(self.topo.devices) >= 2
            res = {
                "success": success,
                "mission_id": 0,
                "title": self.title,
                "score": 95 if success else 40,
                "stars": 3 if success else 1,
                "xp": 400,
                "coins": 200,
                "passed_objectives": [f"Waktu trial: {int(self._t)} detik", f"Total Biaya: ${cost}"],
                "errors": [] if success else ["Kebutuhan perangkat belum terpenuhi."],
                "elapsed_seconds": self._t
            }
            if success:
                self.game.save.add_rewards(res["xp"], res["coins"])
                self.play("level_up")
            else:
                self.play("failure")
            self.game.scenes.push(MissionReportScene(self.game, res))
            return
        elif self.mode_type == "exam":
            up_links = [l for l in self.topo.links.values() if l.state == "up"]
            passed = len(self.topo.devices) >= 2 and len(up_links) >= 1
            res = {
                "success": passed,
                "mission_id": 0,
                "title": self.title,
                "score": 90 if passed else 55,
                "stars": 3 if passed else 0,
                "xp": 600,
                "coins": 350,
                "passed_objectives": ["Standar kompetensi sertifikasi lulus (>80%)"] if passed else [],
                "errors": [] if passed else ["Konfigurasi topologi belum memenuhi passing score 80%."],
                "elapsed_seconds": self._t
            }
            if passed:
                self.game.save.add_rewards(res["xp"], res["coins"])
                self.play("level_up")
            else:
                self.play("failure")
            self.game.scenes.push(MissionReportScene(self.game, res))
            return
        elif self.mission_id is not None:
            mgr = MissionManager()
            res = mgr.evaluate_mission(self.mission_id, self.topo, self._t)
            if res["success"]:
                self.game.save.add_mission_result(self.mission_id, res["stars"], res["score"], res["elapsed_seconds"])
                self.game.save.add_rewards(res["xp"], res["coins"])
                self.play("level_up")
            else:
                self.play("failure")
            self.game.scenes.push(MissionReportScene(self.game, res))

    # ------------------------------------------------------------ aksi: kabel
    def set_tool(self, tool: str, announce: bool = True) -> None:
        self.pending = None
        self.picker = None
        self.tool = tool
        if tool != "select":
            self.tab = "cables"
        if announce:
            if tool == "select":
                self.log_msg("Mode: Select / Move.")
            else:
                ct = CABLE_TYPES[tool]
                self.log_msg(f"Kabel {ct.label} dipilih. Klik perangkat pertama. ({ct.detail})", "info")
        self.play("click")

    def _cable_click(self, dev, pos) -> None:
        other_kind = None
        if self.pending:
            if dev.id == self.pending["dev"]:
                self.log_msg("Pilih perangkat LAIN sebagai ujung kabel kedua.", "warn")
                return
            other_kind = self.topo.get(self.pending["dev"]).get_port(self.pending["port"]).kind
        entries = self.topo.port_options(dev.id, self.tool, other_kind)
        enabled = [e for e in entries if e["enabled"]]
        label = CABLE_TYPES[self.tool].label
        if not enabled:
            self.play("error")
            self.add_effect((dev.x, dev.y), COLORS["red"])
            self.log_msg(f"'{dev.name}' tidak punya port bebas yang cocok untuk kabel {label}.", "error")
            return
        if len(enabled) == 1:
            self._on_port_chosen(dev.id, enabled[0]["name"])
        else:
            self.picker = PortPicker(entries, pos, self.rect_canvas, f"{dev.name}: pilih port ({label})",
                                     lambda name, did=dev.id: self._on_port_chosen(did, name))

    def _on_port_chosen(self, dev_id: int, port: str) -> None:
        dev = self.topo.get(dev_id)
        if self.pending is None:
            self.pending = {"dev": dev_id, "port": port}
            self.log_msg(f"Kabel dimulai dari {dev.name}:{port}. Klik perangkat tujuan (Esc = batal).")
            return
        a, self.pending = self.pending, None
        da = self.topo.get(a["dev"])
        try:
            link = self.topo.connect(a["dev"], a["port"], dev_id, port, self.tool)
        except CableError as e:
            self.play("error")
            self.add_effect((dev.x, dev.y), COLORS["red"])
            self.log_msg(f"Koneksi ditolak: {e}", "error")
            return
        label = CABLE_TYPES[link.cable].label
        self.link_anim[link.id] = self._t
        ok = link.state == "up"
        self.add_effect((dev.x, dev.y), COLORS["green"] if ok else COLORS["red"], delay=0.35)
        self.add_effect((da.x, da.y), COLORS["green"] if ok else COLORS["red"], delay=0.0)
        if ok:
            self.play("connect")
            self.log_msg(f"{da.name}:{a['port']} <-> {dev.name}:{port} ({label}) LINK UP.", "ok")
        else:
            self.play("failure")
            self.log_msg(f"{da.name}:{a['port']} <-> {dev.name}:{port} ({label}) LINK DOWN. {link.reason}", "warn")

    def link_geometry(self) -> dict:
        groups: dict = {}
        for l in self.topo.links.values():
            groups.setdefault(frozenset((l.a[0], l.b[0])), []).append(l.id)
        geo = {}
        for ids in groups.values():
            ids.sort()
            n = len(ids)
            for i, lid in enumerate(ids):
                l = self.topo.links[lid]
                A, B = self.topo.devices[l.a[0]], self.topo.devices[l.b[0]]
                dx, dy = B.x - A.x, B.y - A.y
                d = math.hypot(dx, dy) or 1.0
                ux, uy = dx / d, dy / d
                off = (i - (n - 1) / 2) * 14
                r = min(34, max(4, d / 2 - 6))
                geo[lid] = ((A.x + ux * r - uy * off, A.y + uy * r + ux * off),
                            (B.x - ux * r - uy * off, B.y - uy * r + ux * off))
        return geo

    def link_at(self, wpos) -> int | None:
        best, best_d = None, LINK_HIT_PX / self.zoom
        for lid, (p1, p2) in self.link_geometry().items():
            d = seg_dist(wpos, p1, p2)
            if d <= best_d:
                best, best_d = lid, d
        return best

    # ------------------------------------------------------------ aksi: umum
    def save_now(self) -> None:
        self.game.save.save_topology(self.SLOT, self.topo.to_dict())
        self.play("notification")
        self.log_msg(f"Topologi disimpan ({len(self.topo.devices)} perangkat, {len(self.topo.links)} kabel).", "ok")

    def clear_click(self) -> None:
        if not self.topo.devices:
            self.log_msg("Kanvas sudah kosong.", "warn")
            return
        if self._t < self._clear_armed_until:
            n = len(self.topo.devices)
            self.topo.clear()
            self.select(None)
            self.pending = None
            self._clear_armed_until = 0
            self.play("disconnect")
            self.log_msg(f"Semua perangkat ({n}) dan kabel dihapus.", "warn")
        else:
            self._clear_armed_until = self._t + 3
            self.log_msg("Klik CLEAR sekali lagi dalam 3 detik untuk menghapus SEMUA perangkat.", "warn")

    def toggle_grid(self) -> None:
        self.show_grid = not self.show_grid
        self.log_msg(f"Grid {'ditampilkan' if self.show_grid else 'disembunyikan'}.")

    def zoom_step(self, direction: int, anchor=None) -> None:
        anchor = anchor or self.rect_canvas.center
        before = self.s2w(*anchor)
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * (1.12 ** direction)))
        after = self.s2w(*anchor)
        self.cam[0] += before[0] - after[0]
        self.cam[1] += before[1] - after[1]

    def fit_view(self) -> None:
        devs = list(self.topo.devices.values())
        if not devs:
            self.cam, self.zoom = [0.0, 0.0], 1.0
            return
        xs, ys = [d.x for d in devs], [d.y for d in devs]
        self.cam = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]
        span_x, span_y = max(xs) - min(xs) + 200, max(ys) - min(ys) + 200
        self.zoom = max(ZOOM_MIN, min(1.5, self.rect_canvas.width / span_x, self.rect_canvas.height / span_y))

    def exit_workspace(self) -> None:
        self.save_now()
        self.game.scenes.pop()

    # ------------------------------------------------------------ input
    def handle_event(self, event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        if self.dialog:
            self.dialog.handle_event(event)
            if self.dialog.closed:
                self.dialog = None
            return
        if self.picker:
            p = self.picker
            if p.handle_event(event):
                if p.closed and self.picker is p:
                    self.picker = None
                return
        if self.rename_buf is not None and event.type == pygame.KEYDOWN:
            self._rename_key(event)
            return
        if self.bottom_tab == "terminal" and event.type == pygame.KEYDOWN:
            if event.key != pygame.K_ESCAPE:
                if self.terminal.handle_event(event):
                    return
        for b in self.toolbar + self._visible_buttons:
            if b.handle_event(event):
                return
        if event.type == pygame.KEYDOWN:
            self._key(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_down(event)
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_move(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_up(event)
        elif event.type == pygame.MOUSEWHEEL:
            self._wheel(event)

    def _rename_key(self, event) -> None:
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.commit_rename()
        elif event.key == pygame.K_ESCAPE:
            self.rename_buf = None
        elif event.key == pygame.K_BACKSPACE:
            self.rename_buf = self.rename_buf[:-1]
        elif event.unicode and event.unicode in ALLOWED_NAME_CHARS and len(self.rename_buf) < 20:
            self.rename_buf += event.unicode

    def _key(self, event) -> None:
        k = event.key
        if k == pygame.K_ESCAPE:
            if self.pending:
                self.pending = None
                self.log_msg("Pemasangan kabel dibatalkan.", "warn")
            elif self.tool != "select":
                self.set_tool("select")
            elif self.selected is not None or self.selected_link is not None:
                self.select(None)
            else:
                self.exit_workspace()
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self.delete_any()
        elif k == pygame.K_r:
            self.rotate_selected()
        elif k == pygame.K_F2:
            self.start_rename()
        elif k == pygame.K_g:
            self.toggle_grid()
        elif k == pygame.K_v:
            self.set_tool("select")
        elif k == pygame.K_c:
            self.open_config()
        elif k == pygame.K_t:
            self.open_terminal()
        elif k == pygame.K_p:
            self.open_ping_tool()
        elif k == pygame.K_n:
            self.open_subnet_calc()
        elif pygame.K_1 <= k < pygame.K_1 + len(CABLE_KEYS):
            self.set_tool(CABLE_KEYS[k - pygame.K_1])
        elif k in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.zoom_step(1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.zoom_step(-1)
        elif k in (pygame.K_0, pygame.K_KP0):
            self.fit_view()
        elif k == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
            self.save_now()

    def _mouse_down(self, event) -> None:
        pos = event.pos
        if event.button == 1:
            if self.rect_bottom.collidepoint(pos):
                for tab_k, tr in getattr(self, "bottom_tab_rects", {}).items():
                    if tr.collidepoint(pos):
                        self.bottom_tab = tab_k
                        self.play("click")
                        return
            for key, rc in self.tab_rects.items():
                if rc.collidepoint(pos):
                    self.tab, self.palette_scroll = key, 0
                    return
            key = self.palette_hit(pos)
            if key:
                if self.tab == "devices":
                    if self.tool != "select":
                        self.set_tool("select", announce=False)
                    self.drag = {"kind": "palette", "type": key, "start": pos, "moved": False}
                else:
                    self.set_tool("select" if key == self.tool else key)
                return
            if self.rect_canvas.collidepoint(pos):
                wpos = self.s2w(*pos)
                dev = self.topo.device_at(*wpos)
                if self.tool != "select":
                    if dev:
                        self._cable_click(dev, pos)
                    else:
                        self.drag = {"kind": "pan", "last": pos}
                    return
                if dev:
                    last_t, last_id = self._last_click
                    if last_id == dev.id and self._t - last_t < 0.4:
                        self.select(dev.id)
                        self.start_rename()
                        return
                    self.select(dev.id)
                    self.drag = {"kind": "device", "id": dev.id, "off": (wpos[0] - dev.x, wpos[1] - dev.y),
                                 "orig": (dev.x, dev.y), "moved": False}
                else:
                    lid = self.link_at(wpos)
                    self.select(None, lid)
                    if lid is None:
                        self.drag = {"kind": "pan", "last": pos}
        elif event.button == 3 and self.pending:
            self.pending = None
            self.log_msg("Pemasangan kabel dibatalkan.", "warn")
        elif event.button in (2, 3) and self.rect_canvas.collidepoint(pos):
            self.drag = {"kind": "pan", "last": pos}

    def _mouse_move(self, event) -> None:
        d = self.drag
        if not d:
            return
        if d["kind"] == "pan":
            self.cam[0] -= (event.pos[0] - d["last"][0]) / self.zoom
            self.cam[1] -= (event.pos[1] - d["last"][1]) / self.zoom
            d["last"] = event.pos
        elif d["kind"] == "palette":
            if math.dist(event.pos, d["start"]) > 6:
                d["moved"] = True
        elif d["kind"] == "device":
            wx, wy = self.s2w(*event.pos)
            nx, ny = snap(wx - d["off"][0]), snap(wy - d["off"][1])
            dev = self.topo.devices[d["id"]]
            if (nx, ny) != (dev.x, dev.y):
                self.topo.move_device(d["id"], nx, ny)
                d["moved"] = True

    def _mouse_up(self, event) -> None:
        d, self.drag = self.drag, None
        if not d or event.button not in (1, 2, 3):
            return
        if d["kind"] == "palette":
            if d["moved"] and self.rect_canvas.collidepoint(event.pos):
                self.place_device(d["type"], *self.s2w(*event.pos))
            elif not d["moved"]:
                cx, cy = self.topo.find_free_spot(*self.cam)
                self.place_device(d["type"], cx, cy)
        elif d["kind"] == "device" and not d["moved"]:
            self._last_click = (self._t, d["id"])
        elif d["kind"] == "device" and d["moved"]:
            dev = self.topo.devices.get(d["id"])
            if dev and self.topo.is_occupied(dev.x, dev.y, exclude=dev.id):
                self.topo.move_device(dev.id, *d["orig"])
                self.play("error")
                self.log_msg(f"Tidak bisa memindah '{dev.name}': posisi sudah terisi.", "error")
            elif dev:
                self.log_msg(f"'{dev.name}' dipindah ke ({int(dev.x) // GRID}, {int(dev.y) // GRID}).")

    def _wheel(self, event) -> None:
        pos = pygame.mouse.get_pos()
        if self.rect_canvas.collidepoint(pos):
            self.zoom_step(event.y, pos)
        elif self.rect_left.collidepoint(pos):
            self.palette_scroll -= event.y * 30
            self._clamp_palette()
        elif self.rect_right.collidepoint(pos):
            self.prop_scroll = max(0, self.prop_scroll - event.y)

    # ------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        self._t += dt
        self.net_engine.update(dt)
        self.terminal.update(dt)
        if self.dialog:
            self.dialog.update(dt)
        pos = pygame.mouse.get_pos()
        self.mouse = pos
        self.hover_id = self.hover_link = None
        if self.rect_canvas.collidepoint(pos) and not self.drag and not self.picker:
            wp = self.s2w(*pos)
            dev = self.topo.device_at(*wp)
            if dev:
                self.hover_id = dev.id
            elif self.tool == "select":
                self.hover_link = self.link_at(wp)
        self.effects = [e for e in self.effects if self._t < e["t0"] + e["dur"]]

    def _device_icon(self, dtype: str, size: int, rotation: int):
        key = (dtype, size, rotation)
        img = self._icons.get(key)
        if img is None:
            base = self.game.assets.device_icon(dtype)
            if base is None:
                base = pygame.Surface((128, 128), pygame.SRCALPHA)
                pygame.draw.rect(base, COLORS["cyan"], (16, 16, 96, 96), 6, border_radius=12)
            img = pygame.transform.smoothscale(base, (size, size))
            if rotation:
                img = pygame.transform.rotate(img, -rotation)
            if len(self._icons) > 500:
                self._icons.clear()
            self._icons[key] = img
        return img

    # ------------------------------------------------------------ draw
    def draw(self, surface) -> None:
        surface.fill(COLORS["bg_dark"])
        self._draw_canvas(surface)
        self._draw_left(surface)
        self._draw_right(surface)
        self._draw_bottom(surface)
        self._draw_top(surface)
        self._draw_drag_ghost(surface)
        if self.picker:
            self.picker.draw(surface, self.game.assets)
        if self.dialog:
            self.dialog.draw(surface)

    def _draw_grid(self, surface) -> None:
        c = self.rect_canvas
        mult = 1
        while GRID * mult * self.zoom < 14:
            mult *= 2
        step = GRID * mult
        for axis in (0, 1):
            half = (c.width if axis == 0 else c.height) / 2 / self.zoom
            v = math.floor((self.cam[axis] - half) / step) * step
            while True:
                s = (c.centerx if axis == 0 else c.centery) + (v - self.cam[axis]) * self.zoom
                if s > (c.right if axis == 0 else c.bottom):
                    break
                color = (30, 52, 90) if round(v / GRID) % 4 == 0 else (18, 32, 58)
                if v == 0:
                    color = (40, 90, 140)
                if axis == 0:
                    pygame.draw.line(surface, color, (s, c.top), (s, c.bottom))
                else:
                    pygame.draw.line(surface, color, (c.left, s), (c.right, s))
                v += step

    def _draw_links(self, surface) -> list:
        leds = []
        mids = []
        for lid, (p1, p2) in self.link_geometry().items():
            l = self.topo.links[lid]
            ct = CABLE_TYPES[l.cable]
            t0 = self.link_anim.get(lid)
            prog = 1.0 if t0 is None else min(1.0, (self._t - t0) / 0.35)
            if prog >= 1.0:
                self.link_anim.pop(lid, None)
            s1, s2f = self.w2s(*p1), self.w2s(*p2)
            s2 = lerp_pt(s1, s2f, prog)
            color = ct.color if l.state == "up" else lerp_col(ct.color, COLORS["red"], 0.55)
            width = max(2, int(ct.width * self.zoom))
            if lid == self.selected_link or lid == self.hover_link:
                pygame.draw.line(surface, COLORS["cyan"] if lid == self.selected_link else COLORS["blue"], s1, s2, width + 6)
            draw_styled_line(surface, color, s1, s2, width, ct.style, self.zoom)
            if prog < 1.0:
                pygame.draw.circle(surface, (255, 255, 255), s2, max(4, int(6 * self.zoom)))
            else:
                led = COLORS["green"] if l.state == "up" else COLORS["red"]
                leds += [(s1, led), (s2f, led)]
                if l.state == "down":
                    mids.append(lerp_pt(s1, s2f, 0.5))
        for m in mids:
            r = max(4, int(6 * self.zoom))
            pygame.draw.line(surface, COLORS["red"], (m[0] - r, m[1] - r), (m[0] + r, m[1] + r), 3)
            pygame.draw.line(surface, COLORS["red"], (m[0] - r, m[1] + r), (m[0] + r, m[1] - r), 3)
        return leds

    def _draw_effects(self, surface) -> None:
        for e in self.effects:
            t = (self._t - e["t0"]) / e["dur"]
            if t < 0:
                continue
            sx, sy = self.w2s(*e["pos"])
            col = lerp_col(e["color"], BG, t)
            pygame.draw.circle(surface, col, (sx, sy), max(2, int((12 + 44 * t) * self.zoom)), 3)

    def _draw_packets(self, surface) -> None:
        for pkt in self.net_engine.packets.active_packets:
            if pkt.current_link_id not in self.topo.links:
                continue
            link = self.topo.links[pkt.current_link_id]
            da, db = self.topo.devices.get(link.a[0]), self.topo.devices.get(link.b[0])
            if not da or not db:
                continue
            p_start = (da.x, da.y) if pkt.from_dev_id == da.id else (db.x, db.y)
            p_end = (db.x, db.y) if pkt.from_dev_id == da.id else (da.x, da.y)
            s_start = self.w2s(*p_start)
            s_end = self.w2s(*p_end)
            pos = lerp_pt(s_start, s_end, pkt.progress)

            radius = max(5, int(7 * self.zoom))
            pulse = math.sin(self._t * 12) * 2
            pygame.draw.circle(surface, (255, 255, 255), (int(pos[0]), int(pos[1])), int(radius + pulse + 2), 1)
            pygame.draw.circle(surface, pkt.color, (int(pos[0]), int(pos[1])), radius)
            pygame.draw.circle(surface, (255, 255, 255), (int(pos[0]), int(pos[1])), max(2, radius - 3))

            lbl = get_font(10, True).render(pkt.protocol, True, COLORS["text"])
            surface.blit(lbl, (int(pos[0]) - lbl.get_width() // 2, int(pos[1]) - radius - 12))

    def _draw_canvas(self, surface) -> None:
        c = self.rect_canvas
        surface.set_clip(c)
        pygame.draw.rect(surface, BG, c)
        if self.show_grid:
            self._draw_grid(surface)
        leds = self._draw_links(surface)
        self._draw_packets(surface)
        base = max(24, int(ICON_WORLD * self.zoom))
        name_font = get_font(max(11, min(18, int(13 * self.zoom))), True)
        for dev in self.topo.devices.values():
            sx, sy = self.w2s(dev.x, dev.y)
            if not c.inflate(base * 2, base * 2).collidepoint(sx, sy):
                continue
            k = 1.0
            t0 = self.spawn.get(dev.id)
            if t0 is not None:
                p = (self._t - t0) / 0.3
                if p >= 1:
                    self.spawn.pop(dev.id, None)
                else:
                    k = max(0.2, 0.4 + 0.6 * ease_out_back(max(0.0, p)))
            size = max(12, int(base * k) // 4 * 4)
            icon = self._device_icon(dev.type, size, dev.rotation)
            rect = icon.get_rect(center=(sx, sy))
            if dev.id == self.selected:
                pygame.draw.rect(surface, COLORS["cyan"], rect.inflate(14, 14), 2, border_radius=10)
            elif dev.id == self.hover_id:
                col = COLORS["green"] if self.tool != "select" else COLORS["blue"]
                pygame.draw.rect(surface, col, rect.inflate(10, 10), 2, border_radius=10)
            if self.pending and self.pending["dev"] == dev.id:
                pygame.draw.rect(surface, CABLE_TYPES[self.tool].color, rect.inflate(18, 18), 3, border_radius=12)
            surface.blit(icon, rect)
            pygame.draw.circle(surface, COLORS["green"] if dev.status == "online" else COLORS["red"],
                               (rect.right - 2, rect.top + 4), max(3, int(5 * self.zoom)))
            draw_text(surface, dev.name, name_font, COLORS["text"], (sx, rect.bottom + 6), "midtop")
        for (pt, col) in leds:   # LED port di ujung kabel
            r = max(3, int(5 * self.zoom))
            pygame.draw.circle(surface, BG, pt, r + 2)
            pygame.draw.circle(surface, col, pt, r)
        if self.pending:
            a = self.topo.devices.get(self.pending["dev"])
            if a:
                ct = CABLE_TYPES[self.tool]
                draw_styled_line(surface, ct.color, self.w2s(a.x, a.y), self.mouse, max(2, int(ct.width * self.zoom)), "dashed", self.zoom)
        self._draw_effects(surface)
        if not self.topo.devices:
            draw_text(surface, "Kanvas kosong - seret perangkat dari sidebar kiri ke sini",
                      get_font(16), COLORS["text_dim"], c.center, "center")
        self._draw_banner(surface)
        surface.set_clip(None)
        pygame.draw.rect(surface, COLORS["blue"], c, 1)

    def _draw_banner(self, surface) -> None:
        if self.tool == "select":
            return
        ct = CABLE_TYPES[self.tool]
        if self.pending:
            a = self.topo.devices[self.pending["dev"]]
            msg = f"{ct.label}: dari {a.name}:{self.pending['port']} -> klik perangkat tujuan  (Esc/klik kanan = batal)"
        else:
            msg = f"{ct.label}: klik perangkat pertama  (Esc = kembali ke Select)"
        font = get_font(13, True)
        msg = fit_text(font, msg, self.rect_canvas.width - 28)
        w = font.size(msg)[0] + 16
        box = pygame.Rect(self.rect_canvas.x + 8, self.rect_canvas.y + 8, w, 26)
        pygame.draw.rect(surface, COLORS["bg_panel"], box, border_radius=6)
        pygame.draw.rect(surface, ct.color, box, 2, border_radius=6)
        draw_text(surface, msg, font, COLORS["text"], (box.x + 8, box.centery), "midleft")

    def _draw_top(self, surface) -> None:
        pygame.draw.rect(surface, COLORS["bg_panel"], self.rect_top)
        pygame.draw.line(surface, COLORS["blue"], (0, self.top_h - 1), (self.rect_top.right, self.top_h - 1), 2)
        font = get_font(14, True)
        for b in self.toolbar:
            if b.label == "CLEAR" and self._t < self._clear_armed_until:
                b.label = "SURE?"
            elif b.label == "SURE?" and self._t >= self._clear_armed_until:
                b.label = "CLEAR"
            b.draw(surface, font)
        right_x = self.rect_top.right - 12
        last = self.toolbar[-1].rect.right + 16
        if self.mission_id is not None and self.mission_data:
            time_left = max(0, int(self.mission_data.get("time_limit", 300) - self._t))
            cost = self.topo.total_cost()
            budget = self.mission_data.get("budget", 1000)
            txt = f"{self.title} | Waktu: {time_left}s | Biaya: ${cost}/${budget}"
        elif self.mode_type == "troubleshoot":
            txt = f"[INCIDENT] {self.title} | Investigasi Gangguan & Perbaiki via CLI"
        elif self.mode_type == "challenge":
            cost = self.topo.total_cost()
            txt = f"[TRIAL] {self.title} | Biaya: ${cost} | Waktu: {int(self._t)}s"
        elif self.mode_type == "exam":
            txt = f"[EXAM] {self.title} | Passing Score: 80% | Waktu: {int(self._t)}s"
        else:
            tool = "Select" if self.tool == "select" else CABLE_TYPES[self.tool].label
            txt = f"{self.title} | {tool} | {len(self.topo.devices)} dev | {int(self.zoom * 100)}%"
        draw_text(surface, fit_text(get_font(14), txt, max(40, right_x - last)), get_font(14), COLORS["cyan"], (right_x, 24), "midright")

    def _draw_left(self, surface) -> None:
        r = self.rect_left
        pygame.draw.rect(surface, COLORS["bg_panel"], r)
        pygame.draw.line(surface, COLORS["blue"], (r.right - 1, r.top), (r.right - 1, r.bottom), 2)
        for key, rc in self.tab_rects.items():
            active = key == self.tab
            pygame.draw.rect(surface, COLORS["bg_panel_light"] if active else COLORS["bg_dark"], rc, border_radius=6)
            pygame.draw.rect(surface, COLORS["cyan"] if active else COLORS["gray"], rc, 2 if active else 1, border_radius=6)
            draw_text(surface, key.upper(), get_font(13, True), COLORS["cyan"] if active else COLORS["text_dim"], rc.center, "center")
        surface.set_clip(pygame.Rect(r.x, r.y + 36, r.width, r.height - 36))
        hover = self.palette_hit(self.mouse)
        small, tiny = get_font(14, True), get_font(12)
        for i, key in enumerate(self.current_items()):
            ir = self.palette_item_rect(i)
            if ir.bottom < r.y + 36 or ir.top > r.bottom:
                continue
            active = self.tab == "cables" and key == self.tool
            pygame.draw.rect(surface, COLORS["bg_panel_light"] if (key == hover or active) else COLORS["bg_dark"], ir, border_radius=8)
            pygame.draw.rect(surface, COLORS["cyan"] if (key == hover or active) else COLORS["gray"], ir, 2 if active else 1, border_radius=8)
            tx = ir.x + 52
            if self.tab == "devices":
                spec = self.topo.catalog[key]
                icon = self.game.assets.image(f"devices/{key}_small.png", (40, 40))
                if icon:
                    surface.blit(icon, icon.get_rect(midleft=(ir.x + 6, ir.centery)))
                draw_text(surface, fit_text(small, spec["label"], ir.right - tx - 4), small, COLORS["text"], (tx, ir.y + 8))
                draw_text(surface, f"{spec['cost']} coins" if spec["cost"] else "gratis", tiny, COLORS["yellow"], (tx, ir.y + 28))
            elif key == "select":
                icon = self.game.assets.image("icons/select.png", (32, 32))
                if icon:
                    surface.blit(icon, icon.get_rect(midleft=(ir.x + 10, ir.centery)))
                draw_text(surface, "Select / Move", small, COLORS["text"], (tx, ir.y + 8))
                draw_text(surface, fit_text(tiny, "Pilih, pindah (V)", ir.right - tx - 4), tiny, COLORS["text_dim"], (tx, ir.y + 28))
            else:
                ct = CABLE_TYPES[key]
                sw = self.game.assets.image(f"ui/cable_{key}.png", (44, 11))
                if sw:
                    surface.blit(sw, sw.get_rect(midleft=(ir.x + 4, ir.centery)))
                draw_text(surface, fit_text(small, ct.label, ir.right - tx - 4), small, ct.color, (tx, ir.y + 6))
                draw_text(surface, fit_text(tiny, f"[{CABLE_KEYS.index(key) + 1}] {ct.summary}", ir.right - tx - 4), tiny, COLORS["text_dim"], (tx, ir.y + 28))
        surface.set_clip(None)
        total, view = len(self.current_items()) * ITEM_H, r.height - 40
        if total > view:
            bar_h = max(24, int(view * view / total))
            bar_y = r.y + 38 + int((view - bar_h) * self.palette_scroll / (total - view))
            pygame.draw.rect(surface, COLORS["cyan"], (r.right - 5, bar_y, 3, bar_h), border_radius=2)

    def _draw_right(self, surface) -> None:
        r = self.rect_right
        pygame.draw.rect(surface, COLORS["bg_panel"], r)
        pygame.draw.line(surface, COLORS["blue"], (r.left, r.top), (r.left, r.bottom), 2)
        draw_text(surface, "PROPERTIES", get_font(16, True), COLORS["cyan"], (r.centerx, r.y + 18), "center")
        font, bold = get_font(14), get_font(14, True)
        x, y, mw = r.x + 12, r.y + 42, r.width - 24
        self._visible_buttons = []
        if self.sel_link:
            self._draw_link_props(surface, x, y, mw, font, bold)
            return
        dev = self.sel_dev
        if not dev:
            draw_text(surface, "Ringkasan topologi", bold, COLORS["text"], (x, y)); y += 26
            up = sum(1 for l in self.topo.links.values() if l.state == "up")
            down = len(self.topo.links) - up
            for text, col in ((f"Perangkat : {len(self.topo.devices)}", COLORS["text"]),
                              (f"Kabel     : {len(self.topo.links)} ({up} up, {down} down)", COLORS["text"]),
                              (f"Biaya     : {self.topo.total_cost()} coins", COLORS["yellow"])):
                draw_text(surface, fit_text(font, text, mw), font, col, (x, y)); y += 20
            y += 8
            for t, n in self.topo.counts().items():
                if y > r.bottom - 24:
                    break
                draw_text(surface, fit_text(font, f"{self.topo.catalog[t]['label']}: {n}", mw), font, COLORS["text_dim"], (x, y)); y += 20
            if not self.topo.devices:
                draw_text(surface, "Pilih perangkat di kanvas", font, COLORS["text_dim"], (x, y + 8))
            return
        from devices.base_device import short_port_name
        from networking.ip_address import ip_to_str
        if dev.ip_role == "host":
            p0 = next((p for p in dev.ip_ports() if p.ip is not None), None)
            ip_txt = f"{ip_to_str(p0.ip)}/{p0.prefix}" if p0 else "belum diatur"
        elif dev.ip_role == "router":
            n_if = sum(1 for p in dev.ip_ports() if p.ip is not None)
            ip_txt = f"{n_if} interface ber-IP" if n_if else "belum diatur"
        else:
            ip_txt = "- (layer 2)"
        rows = [("Nama", dev.name, COLORS["cyan"]), ("Tipe", dev.label, COLORS["text"]), ("Model", dev.model, COLORS["text"]),
                ("Status", dev.status.upper(), COLORS["green"] if dev.status == "online" else COLORS["red"]),
                ("MAC", dev.mac, COLORS["text"]), ("IP", ip_txt, COLORS["text"] if "/" in ip_txt else COLORS["text_dim"])]
        if dev.ip_role == "host":
            rows.append(("Gateway", ip_to_str(dev.gateway) if dev.gateway is not None else "-", COLORS["text"] if dev.gateway is not None else COLORS["text_dim"]))
        rows.append(("Posisi", f"({int(dev.x) // GRID}, {int(dev.y) // GRID}) rot {dev.rotation}", COLORS["text_dim"]))
        narrow = r.width < 240
        lab_w, vfont = (64, get_font(12)) if narrow else (70, font)
        for k, v, col in rows:
            draw_text(surface, f"{'GW' if narrow and k == 'Gateway' else k}:", font, COLORS["text_dim"], (x, y))
            draw_text(surface, fit_text(vfont, v, mw - lab_w), vfont, col, (x + lab_w, y)); y += 20
        if self.rename_buf is not None:
            y += 4
            box = pygame.Rect(x, y, mw, 28)
            pygame.draw.rect(surface, COLORS["bg_dark"], box, border_radius=6)
            pygame.draw.rect(surface, COLORS["cyan"], box, 2, border_radius=6)
            caret = "_" if int(self._t * 2) % 2 == 0 else " "
            draw_text(surface, fit_text(bold, self.rename_buf + caret, mw - 10)[-22:], bold, COLORS["text"], (box.x + 6, box.centery), "midleft")
            y = box.bottom + 4
            draw_text(surface, "Enter=OK  Esc=Batal", get_font(12), COLORS["text_dim"], (x, y)); y += 22
        by, half = y + 6, (mw - 6) // 2
        pb = self.prop_buttons
        pb["rename"].rect, pb["rotate"].rect = pygame.Rect(x, by, half, 28), pygame.Rect(x + half + 6, by, half, 28)
        by += 34
        layout = [pb["rename"], pb["rotate"]]
        if dev.ip_role != "none":
            pb["config"].rect = pygame.Rect(x, by, mw, 28)
            by += 34
            layout.append(pb["config"])
        pb["terminal"].rect = pygame.Rect(x, by, half, 28)
        pb["ping"].rect = pygame.Rect(x + half + 6, by, half, 28)
        by += 34
        layout.extend([pb["terminal"], pb["ping"]])
        pb["delete"].rect = pygame.Rect(x, by, mw, 28)
        layout.append(pb["delete"])
        for b in layout:
            b.draw(surface, get_font(13, True))
            self._visible_buttons.append(b)
        y = by + 36
        draw_text(surface, f"Port ({len(dev.ports)})  scroll=lihat", bold if r.width > 200 else get_font(13, True), COLORS["text"], (x, y)); y += 22
        small = get_font(12)
        lines = []
        for p in dev.ports:
            st = self.topo.port_state(p)
            text = f"{short_port_name(p.name)} [{p.kind}]"
            if p.connected_to:
                rd = self.topo.devices.get(p.connected_to[0])
                if rd:
                    text += f" > {rd.name}"
            lines.append((st, text, COLORS["text"] if st != "off" else COLORS["text_dim"]))
            if p.ip is not None:
                lines.append((None, f"{ip_to_str(p.ip)}/{p.prefix}", COLORS["cyan"]))
        visible = max(1, (r.bottom - 8 - y) // 18)
        self.prop_scroll = max(0, min(self.prop_scroll, max(0, len(lines) - visible)))
        for st, text, col in lines[self.prop_scroll:self.prop_scroll + visible]:
            if st is not None:
                led = self.game.assets.image(f"ui/led_{ {'off': 'off', 'up': 'green', 'down': 'red'}[st] }.png")
                if led:
                    surface.blit(led, (x, y + 1))
                draw_text(surface, fit_text(small, text, mw - 22), small, col, (x + 22, y))
            else:
                draw_text(surface, fit_text(small, text, mw - 22), small, col, (x + 22, y))
            y += 18

    def _draw_link_props(self, surface, x, y, mw, font, bold) -> None:
        l = self.sel_link
        ct = CABLE_TYPES[l.cable]
        da, db = self.topo.devices[l.a[0]], self.topo.devices[l.b[0]]
        up = l.state == "up"
        rows = [("Kabel", ct.label, ct.color), ("Status", "LINK UP" if up else "LINK DOWN", COLORS["green"] if up else COLORS["red"]),
                ("Ujung A", f"{da.name}", COLORS["text"]), ("", l.a[1], COLORS["text_dim"]),
                ("Ujung B", f"{db.name}", COLORS["text"]), ("", l.b[1], COLORS["text_dim"])]
        for k, v, col in rows:
            if k:
                draw_text(surface, f"{k}:", font, COLORS["text_dim"], (x, y))
            draw_text(surface, fit_text(font, v, mw - 80), font, col, (x + 80, y)); y += 20
        y += 6
        draw_text(surface, "Diagnosa kabel", bold, COLORS["cyan"], (x, y)); y += 22
        for line in wrap_text(font, l.reason or "-", mw)[:7]:
            draw_text(surface, line, font, COLORS["text"] if up else COLORS["yellow"], (x, y)); y += 18
        b = self.prop_buttons["disconnect"]
        b.rect = pygame.Rect(x, y + 10, mw, 30)
        b.draw(surface, get_font(14, True))
        self._visible_buttons.append(b)

    def _draw_bottom(self, surface) -> None:
        r = self.rect_bottom
        pygame.draw.rect(surface, (6, 11, 22), r)
        pygame.draw.line(surface, COLORS["blue"], (r.left, r.top), (r.right, r.top), 2)

        # Tab bar di panel bawah
        tab_h = 22
        tab_log_r = pygame.Rect(r.x + 8, r.y + 4, 100, tab_h)
        tab_pkt_r = pygame.Rect(r.x + 114, r.y + 4, 130, tab_h)
        tab_cli_r = pygame.Rect(r.x + 250, r.y + 4, 120, tab_h)
        self.bottom_tab_rects = {"log": tab_log_r, "packets": tab_pkt_r, "terminal": tab_cli_r}

        for tab_k, tr in self.bottom_tab_rects.items():
            active = (self.bottom_tab == tab_k)
            col_bg = COLORS["bg_panel_light"] if active else COLORS["bg_panel"]
            col_bd = COLORS["cyan"] if active else COLORS["gray"]
            pygame.draw.rect(surface, col_bg, tr, border_radius=4)
            pygame.draw.rect(surface, col_bd, tr, 1, border_radius=4)
            label = {"log": "EVENT LOG", "packets": "PACKET MONITOR", "terminal": "CLI TERMINAL"}[tab_k]
            draw_text(surface, label, get_font(11, True), COLORS["cyan"] if active else COLORS["text_dim"], tr.center, "center")

        content_rect = pygame.Rect(r.x, r.y + 28, r.width, r.height - 28)

        if self.bottom_tab == "terminal":
            self.terminal.draw(surface, content_rect)
        elif self.bottom_tab == "packets":
            self.packet_monitor.draw(surface, content_rect)
        else:
            font = get_font(13)
            lh = 17
            fit = max(1, (content_rect.height - 8) // lh)
            for i, (ts, msg, lvl) in enumerate(self.log[-fit:]):
                yy = content_rect.y + 4 + i * lh
                draw_text(surface, ts, font, COLORS["text_dim"], (content_rect.x + 10, yy))
                draw_text(surface, fit_text(font, msg, content_rect.width - 70), font, LOG_COLORS[lvl], (content_rect.x + 56, yy))

    def _draw_drag_ghost(self, surface) -> None:
        d = self.drag
        if not d or d["kind"] != "palette" or not d["moved"]:
            return
        over = self.rect_canvas.collidepoint(self.mouse)
        size = max(24, int(ICON_WORLD * self.zoom)) if over else 48
        icon = self._device_icon(d["type"], size, 0).copy()
        icon.set_alpha(170)
        surface.blit(icon, icon.get_rect(center=self.mouse))
        if over:
            wx, wy = self.s2w(*self.mouse)
            gx, gy = self.w2s(snap(wx), snap(wy))
            pygame.draw.circle(surface, COLORS["cyan"], (gx, gy), 4)
