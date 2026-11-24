"""Subnetting Calculator: info subnet, pemecahan subnet, dan VLSM."""
from __future__ import annotations

import pygame

from config import COLORS
from interface.forms import IP_CHARS, MASK_CHARS, Dialog, TextField
from interface.widgets import Button, draw_text, fit_text, get_font
from networking.ip_address import IPv4Error, ip_to_str, parse_ip, parse_mask
from networking.subnetting import SubnetError, SubnetInfo, split_subnet, vlsm

TABS = ("SUBNET INFO + SPLIT", "VLSM")


class SubnetCalculatorDialog(Dialog):
    def __init__(self, workspace) -> None:
        super().__init__(workspace)
        self.tab = 0
        self.f_ip = TextField("192.168.1.0", IP_CHARS, 15, "192.168.1.0")
        self.f_mask = TextField("/24", MASK_CHARS, 15, "/24 atau 255.255.255.0")
        self.f_split = TextField("/26", MASK_CHARS, 15, "kosong = tanpa split")
        self.f_base = TextField("192.168.10.0/24", MASK_CHARS, 18, "192.168.10.0/24")
        self.f_hosts = TextField("100, 50, 25, 10", set("0123456789, "), 40, "100, 50, 25, 10")
        self.sets = [[self.f_ip, self.f_mask, self.f_split], [self.f_base, self.f_hosts]]
        self.focus = 0
        self.scroll = 0
        self._key = None
        self.info: list[tuple[str, str]] = []
        self.header: list[str] = []
        self.rows: list[list[str]] = []
        self.note = ""
        self.error = ""
        self.btn_close = Button("CLOSE (Esc)", self.close)
        self.layout(workspace.game.screen.get_size())
        self._set_focus(0)

    @property
    def fields(self): return self.sets[self.tab]

    def close(self) -> None:
        self.closed = True

    def _set_focus(self, i: int) -> None:
        for f in self.fields:
            f.focused = False
        self.focus = i % len(self.fields)
        self.fields[self.focus].focused = True

    def layout(self, size) -> None:
        super().layout(size)
        w, h = size
        self.rect = pygame.Rect(0, 0, min(w - 24, 780), min(h - 16, 560))
        self.rect.center = (w // 2, h // 2)
        x = self.rect.x + 20
        self.tab_rects = [pygame.Rect(x + i * 210, self.rect.y + 54, 200, 28) for i in range(len(TABS))]
        fy, fw = self.rect.y + 106, (self.rect.width - 40 - 20) // 3
        for i, f in enumerate([self.f_ip, self.f_mask, self.f_split]):
            f.rect = pygame.Rect(x + i * (fw + 10), fy, fw, 30)
        self.f_base.rect = pygame.Rect(x, fy, 250, 30)
        self.f_hosts.rect = pygame.Rect(x + 260, fy, self.rect.width - 40 - 260, 30)
        self.btn_close.rect = pygame.Rect(self.rect.right - 170, self.rect.bottom - 44, 150, 32)

    # ---------------------------------------------------------- hitung
    def _compute(self) -> None:
        key = (self.tab, tuple(f.text for f in self.fields))
        if key == self._key:
            return
        self._key, self.info, self.header, self.rows, self.note, self.error = key, [], [], [], "", ""
        self.scroll = 0
        try:
            if self.tab == 0:
                base = SubnetInfo(parse_ip(self.f_ip.text), parse_mask(self.f_mask.text))
                self.info = base.describe()
                if self.f_split.text.strip():
                    new_p = parse_mask(self.f_split.text)
                    count, subs = split_subnet(base, new_p, limit=1024)
                    self.header = ["#", "Network/CIDR", "Host pertama", "Host terakhir", "Broadcast", "Host"]
                    self.rows = [[str(i + 1), s.cidr(), ip_to_str(s.first_host), ip_to_str(s.last_host), ip_to_str(s.broadcast), f"{s.usable_hosts:,}"]
                                 for i, s in enumerate(subs)]
                    self.note = f"{base.cidr()} dipecah menjadi {count:,} subnet /{new_p}" + (f" (ditampilkan {len(subs)} pertama)" if count > len(subs) else "")
            else:
                txt = self.f_base.text.strip()
                if "/" not in txt:
                    raise IPv4Error("Isi jaringan induk dengan format 192.168.10.0/24.")
                ip_t, mask_t = txt.split("/", 1)
                base = SubnetInfo(parse_ip(ip_t), parse_mask(mask_t))
                demands = [int(x) for x in self.f_hosts.text.replace(",", " ").split()]
                out = vlsm(base, demands)
                self.header = ["Subnet", "Butuh", "Network/CIDR", "Host pertama", "Host terakhir", "Broadcast", "Usable"]
                self.rows = [[a.label, str(a.hosts_needed), a.info.cidr(), ip_to_str(a.info.first_host), ip_to_str(a.info.last_host),
                              ip_to_str(a.info.broadcast), f"{a.info.usable_hosts:,}"] for a in out]
                used = sum(a.info.total_addresses for a in out)
                self.note = f"Induk {base.cidr()}: terpakai {used:,} dari {base.total_addresses:,} alamat (sisa {base.total_addresses - used:,}). Urut dari kebutuhan terbesar."
        except (IPv4Error, SubnetError, ValueError) as e:
            self.error = str(e)

    # ---------------------------------------------------------- input
    def handle_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                self.close()
            elif k == pygame.K_TAB:
                self._set_focus(self.focus + (-1 if event.mod & pygame.KMOD_SHIFT else 1))
            elif k == pygame.K_PAGEDOWN:
                self.scroll += 5
            elif k == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 5)
            elif k == pygame.K_DOWN:
                self.scroll += 1
            elif k == pygame.K_UP:
                self.scroll = max(0, self.scroll - 1)
            else:
                self.fields[self.focus].handle_key(event)
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * 2)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.tab_rects):
                if r.collidepoint(event.pos) and i != self.tab:
                    self.tab = i
                    self._set_focus(0)
            for i, f in enumerate(self.fields):
                if f.click(event.pos):
                    self._set_focus(i)
        self.btn_close.handle_event(event)
        return True

    # ---------------------------------------------------------- draw
    def draw(self, surface) -> None:
        self._compute()
        self.draw_frame(surface, "SUBNETTING CALCULATOR")
        font, bold, small = get_font(14), get_font(14, True), get_font(12)
        x = self.rect.x + 20
        for i, r in enumerate(self.tab_rects):
            active = i == self.tab
            pygame.draw.rect(surface, COLORS["bg_panel_light"] if active else COLORS["bg_dark"], r, border_radius=6)
            pygame.draw.rect(surface, COLORS["cyan"] if active else COLORS["gray"], r, 2 if active else 1, border_radius=6)
            draw_text(surface, TABS[i], get_font(12, True), COLORS["cyan"] if active else COLORS["text_dim"], r.center, "center")
        labels = [("IP ADDRESS", self.f_ip), ("SUBNET MASK / PREFIX", self.f_mask), ("SPLIT KE PREFIX (opsional)", self.f_split)] if self.tab == 0 \
            else [("JARINGAN INDUK", self.f_base), ("KEBUTUHAN HOST PER SUBNET (pisah koma)", self.f_hosts)]
        for text, f in labels:
            draw_text(surface, fit_text(small, text, f.rect.width), small, COLORS["text_dim"], (f.rect.x, f.rect.y - 16))
            f.draw(surface, font, self.t)
        y = self.rect.y + 148
        if self.error:
            draw_text(surface, fit_text(font, self.error, self.rect.width - 40), font, COLORS["yellow"], (x, y))
            y += 24
        if self.info:
            half = (self.rect.width - 40) // 2
            for i, (k, v) in enumerate(self.info):
                cx, cy = x + (i // 5) * half, y + (i % 5) * 19
                draw_text(surface, f"{k}:", font, COLORS["text_dim"], (cx, cy))
                draw_text(surface, fit_text(font, v, half - 130), font, COLORS["cyan"] if i == 0 else COLORS["text"], (cx + 130, cy))
            y += 5 * 19 + 10
        if self.note:
            draw_text(surface, fit_text(small, self.note, self.rect.width - 40), small, COLORS["green"], (x, y)); y += 20
        if self.rows:
            self._draw_table(surface, x, y)

    def _draw_table(self, surface, x, y) -> None:
        small = get_font(12)
        total_w = self.rect.width - 40
        weights = [0.07, 0.19, 0.17, 0.17, 0.17, 0.10] if len(self.header) == 6 else [0.09, 0.07, 0.19, 0.17, 0.17, 0.17, 0.10]
        cols, cx = [], x
        for wgt in weights:
            cols.append(cx)
            cx += int(total_w * wgt)
        for c, h in zip(cols, self.header):
            draw_text(surface, h, small, COLORS["cyan"], (c, y))
        pygame.draw.line(surface, COLORS["blue"], (x, y + 16), (x + total_w, y + 16))
        avail = max(1, (self.rect.bottom - 56 - (y + 20)) // 18)
        self.scroll = max(0, min(self.scroll, max(0, len(self.rows) - avail)))
        for i, row in enumerate(self.rows[self.scroll:self.scroll + avail]):
            yy = y + 20 + i * 18
            if i % 2 == 0:
                pygame.draw.rect(surface, (14, 24, 44), (x - 4, yy - 1, total_w + 8, 18))
            for c, w_, cell in zip(cols, weights, row):
                draw_text(surface, fit_text(small, cell, int(total_w * w_) - 6), small, COLORS["text"], (c, yy))
        if len(self.rows) > avail:
            draw_text(surface, f"{self.scroll + 1}-{min(len(self.rows), self.scroll + avail)} dari {len(self.rows)}  (scroll / PgUp / PgDn)",
                      small, COLORS["text_dim"], (x, self.rect.bottom - 38))
        self.btn_close.draw(surface, get_font(13, True))
