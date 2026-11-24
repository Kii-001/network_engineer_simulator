"""Device Configuration Panel: konfigurasi IP interface dan default gateway."""
from __future__ import annotations

import pygame

from config import COLORS
from devices.base_device import short_port_name
from engine.topology_engine import KEEP, IPConfigError
from interface.forms import IP_CHARS, MASK_CHARS, Dialog, TextField
from interface.widgets import Button, draw_text, fit_text, get_font, wrap_text
from networking.ip_address import IPv4Error, ip_to_str, mask_to_str, parse_ip, parse_mask
from networking.subnetting import SubnetInfo, host_address_error

STATE_COL = {"up": COLORS["green"], "down": COLORS["red"], "off": COLORS["text_dim"]}
STATE_TXT = {"up": "LINK UP", "down": "LINK DOWN", "off": "tanpa kabel"}


class DeviceConfigDialog(Dialog):
    def __init__(self, workspace, dev) -> None:
        super().__init__(workspace)
        self.dev = dev
        self.rows = []
        for p in dev.ip_ports():
            ip = TextField(ip_to_str(p.ip) if p.ip is not None else "", IP_CHARS, 15, "192.168.1.10")
            mask = TextField(mask_to_str(p.prefix) if p.prefix is not None else "", MASK_CHARS, 15, "255.255.255.0")
            self.rows.append({"port": p, "ip": ip, "mask": mask})
        self.gw = TextField(ip_to_str(dev.gateway) if dev.gateway is not None else "", IP_CHARS, 15, "192.168.1.1") \
            if dev.ip_role == "host" else None
        self.fields = [f for r in self.rows for f in (r["ip"], r["mask"])] + ([self.gw] if self.gw else [])
        self.focus = 0
        self.fields[0].focused = True
        self.msg, self.msg_col = "Isi IP dan mask, lalu APPLY (Enter). Mask boleh 255.255.255.0 atau /24.", COLORS["text_dim"]
        self.btn_apply = Button("APPLY (Enter)", self.apply)
        self.btn_clear = Button("CLEAR ALL", self.clear_all)
        self.btn_cancel = Button("CANCEL (Esc)", self.close)
        self.layout(workspace.game.screen.get_size())

    # ---------------------------------------------------------- layout
    def layout(self, size) -> None:
        super().layout(size)
        w, h = size
        n = len(self.rows)
        need = 60 + 26 + n * 42 + (48 if self.gw else 0) + 110 + 90
        self.rect = pygame.Rect(0, 0, min(w - 30, 700), min(h - 20, need))
        self.rect.center = (w // 2, h // 2)
        x, avail = self.rect.x + 20, self.rect.width - 40
        self.label_w = int(avail * 0.34)
        fw = (avail - self.label_w - 10) // 2
        y0 = self.rect.y + 80
        for i, r in enumerate(self.rows):
            y = y0 + i * 42
            r["y"] = y
            r["ip"].rect = pygame.Rect(x + self.label_w, y, fw, 30)
            r["mask"].rect = pygame.Rect(x + self.label_w + fw + 10, y, fw, 30)
        y = y0 + n * 42
        if self.gw:
            self.gw_y = y + 6
            self.gw.rect = pygame.Rect(x + self.label_w, self.gw_y, fw, 30)
            y += 48
        self.info_rect = pygame.Rect(x, y + 6, avail, max(40, self.rect.bottom - 100 - (y + 6)))
        by = self.rect.bottom - 48
        bw = min(150, (avail - 20) // 3)
        for i, b in enumerate((self.btn_apply, self.btn_clear, self.btn_cancel)):
            b.rect = pygame.Rect(self.rect.right - 20 - (3 - i) * bw - (2 - i) * 10 + 0, by, bw, 34)

    # ---------------------------------------------------------- aksi
    def close(self) -> None:
        self.closed = True

    def clear_all(self) -> None:
        for f in self.fields:
            f.set_text("")
            f.error = False
        self.msg, self.msg_col = "Semua isian dikosongkan. Tekan APPLY untuk menghapus konfigurasi IP.", COLORS["yellow"]

    def apply(self) -> None:
        ports = {r["port"].name: (r["ip"].text, r["mask"].text) for r in self.rows}
        gw = self.gw.text if self.gw else KEEP
        try:
            self.ws.topo.apply_ip_config(self.dev.id, ports, gw)
        except IPConfigError as e:
            self.msg, self.msg_col = str(e), COLORS["red"]
            for f in self.fields:
                f.error = False
            target = None
            if e.field == "gateway" and self.gw:
                target = self.gw
            else:
                for r in self.rows:
                    if r["port"].name == e.port and e.field in ("ip", "mask"):
                        target = r[e.field]
            if target:
                target.error = True
                self._focus_field(target)
            self.ws.play("error")
            return
        self.closed = True
        self.ws.on_ip_applied(self.dev)

    def _focus_field(self, field) -> None:
        for f in self.fields:
            f.focused = False
        self.focus = self.fields.index(field)
        field.focused = True

    def _move(self, step: int) -> None:
        self._focus_field(self.fields[(self.focus + step) % len(self.fields)])

    # ---------------------------------------------------------- input
    def handle_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                self.close()
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.apply()
            elif k == pygame.K_TAB:
                self._move(-1 if event.mod & pygame.KMOD_SHIFT else 1)
            elif k == pygame.K_DOWN:
                self._move(2 if self.focus + 2 < len(self.fields) else 1 if self.gw and self.focus == len(self.fields) - 2 else 0)
            elif k == pygame.K_UP:
                self._move(-2 if self.focus >= 2 else 0)
            else:
                self.fields[self.focus].handle_key(event)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for f in self.fields:
                if f.click(event.pos):
                    self._focus_field(f)
        for b in (self.btn_apply, self.btn_clear, self.btn_cancel):
            if b.handle_event(event):
                break
        return True

    # ---------------------------------------------------------- info langsung
    def _info_lines(self) -> list[tuple[str, tuple]]:
        f = self.fields[self.focus]
        if f is self.gw:
            try:
                g = parse_ip(self.gw.text)
            except IPv4Error as e:
                return [(f"Gateway: {e}", COLORS["yellow"])]
            for r in self.rows:
                try:
                    info = SubnetInfo(parse_ip(r["ip"].text), parse_mask(r["mask"].text))
                except IPv4Error:
                    continue
                if info.contains(g):
                    ok = host_address_error(g, info.prefix) is None and g != parse_ip(r["ip"].text)
                    return [(f"Gateway berada di subnet {info.cidr()} ({short_port_name(r['port'].name)}).", COLORS["green"] if ok else COLORS["yellow"]),
                            ("OK: gateway harus satu subnet dengan interface." if ok else "Gateway sama dengan alamat network/broadcast/IP sendiri.", COLORS["text_dim"])]
            return [("Gateway di luar subnet interface mana pun - paket keluar subnet tidak akan terkirim.", COLORS["yellow"])]
        row = next(r for r in self.rows if f in (r["ip"], r["mask"]))
        try:
            ip = parse_ip(row["ip"].text)
        except IPv4Error as e:
            return [(f"IP: {e}", COLORS["yellow"])]
        try:
            prefix = parse_mask(row["mask"].text)
        except IPv4Error as e:
            return [(f"Mask: {e}", COLORS["yellow"])]
        info = SubnetInfo(ip, prefix)
        err = host_address_error(ip, prefix)
        lines = [(f"{short_port_name(row['port'].name)}  {ip_to_str(ip)}/{prefix}   mask {mask_to_str(prefix)}", COLORS["cyan"]),
                 (f"Network {ip_to_str(info.network)}  |  Broadcast {ip_to_str(info.broadcast)}", COLORS["text"]),
                 (f"Rentang host {ip_to_str(info.first_host)} - {ip_to_str(info.last_host)}  ({info.usable_hosts:,} host)", COLORS["text"])]
        lines.append((err, COLORS["red"]) if err else ("Alamat valid untuk interface ini.", COLORS["green"]))
        return lines

    # ---------------------------------------------------------- draw
    def draw(self, surface) -> None:
        d = self.dev
        self.draw_frame(surface, f"DEVICE CONFIG - {d.name} ({d.label})  |  IP Configuration")
        font, bold, small = get_font(14), get_font(14, True), get_font(12)
        x = self.rect.x + 20
        draw_text(surface, "INTERFACE", small, COLORS["text_dim"], (x, self.rect.y + 58))
        if self.rows:
            draw_text(surface, "IP ADDRESS", small, COLORS["text_dim"], (self.rows[0]["ip"].rect.x, self.rect.y + 58))
            draw_text(surface, "SUBNET MASK", small, COLORS["text_dim"], (self.rows[0]["mask"].rect.x, self.rect.y + 58))
        for r in self.rows:
            p = r["port"]
            st = self.ws.topo.port_state(p)
            draw_text(surface, fit_text(bold, f"{short_port_name(p.name)} [{p.kind}]", self.label_w - 8), bold, COLORS["text"], (x, r["y"] + 2))
            draw_text(surface, STATE_TXT[st], small, STATE_COL[st], (x, r["y"] + 18))
            r["ip"].draw(surface, font, self.t)
            r["mask"].draw(surface, font, self.t)
        if self.gw:
            draw_text(surface, "Default Gateway", bold, COLORS["text"], (x, self.gw_y + 6))
            self.gw.draw(surface, font, self.t)
        ir = self.info_rect
        pygame.draw.rect(surface, COLORS["bg_dark"], ir, border_radius=8)
        pygame.draw.rect(surface, COLORS["gray"], ir, 1, border_radius=8)
        yy = ir.y + 8
        for text, col in self._info_lines():
            for line in wrap_text(small if len(text) > 70 else font, text, ir.width - 20)[:2]:
                if yy > ir.bottom - 18:
                    break
                draw_text(surface, line, font if len(text) <= 70 else small, col, (ir.x + 10, yy)); yy += 19
        my = self.rect.bottom - 92
        for line in wrap_text(small, self.msg, self.rect.width - 40)[:2]:
            draw_text(surface, line, small, self.msg_col, (x, my)); my += 16
        for b in (self.btn_apply, self.btn_clear, self.btn_cancel):
            b.draw(surface, get_font(13, True))
