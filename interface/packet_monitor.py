"""Packet Monitor: Panel inspeksi paket data real-time dan log pengiriman."""
from __future__ import annotations

import pygame
from config import COLORS
from interface.widgets import get_font
from networking.ip_address import ip_to_str


class PacketMonitorPanel:
    def __init__(self, packet_engine) -> None:
        self.pkt_engine = packet_engine
        self.scroll_offset = 0

    def draw(self, surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, (10, 16, 30), rect)
        pygame.draw.rect(surface, COLORS["blue"], rect, 1)

        font_h = get_font(12, True)
        font_d = get_font(11)

        # Header bar
        header_r = pygame.Rect(rect.x, rect.y, rect.width, 24)
        pygame.draw.rect(surface, COLORS["bg_panel_light"], header_r)
        
        headers = [("ID", 40), ("PROTO", 60), ("SOURCE IP", 110), ("DEST IP", 110), ("STATUS", 80), ("DETAIL / DROP REASON", 240)]
        hx = rect.x + 8
        for title, col_w in headers:
            s = font_h.render(title, True, COLORS["cyan"])
            surface.blit(s, (hx, rect.y + 4))
            hx += col_w

        # Rows
        packets = self.pkt_engine.packet_log
        y = rect.y + 28
        line_h = 18
        max_rows = (rect.height - 32) // line_h

        for pkt in packets[self.scroll_offset : self.scroll_offset + max_rows]:
            if y + line_h > rect.bottom:
                break

            stat_col = COLORS["green"] if pkt.status == "delivered" else (COLORS["yellow"] if pkt.status == "in_flight" else COLORS["red"])
            
            src_str = ip_to_str(pkt.src_ip) if pkt.src_ip is not None else pkt.src_mac[:12]
            dst_str = ip_to_str(pkt.dst_ip) if pkt.dst_ip is not None else pkt.dst_mac[:12]
            reason = pkt.drop_reason or (pkt.hops[-1]["note"] if pkt.hops else "")

            row_data = [
                (f"#{pkt.id}", 40, COLORS["text_dim"]),
                (pkt.protocol, 60, pkt.color),
                (src_str, 110, COLORS["text"]),
                (dst_str, 110, COLORS["text"]),
                (pkt.status.upper(), 80, stat_col),
                (reason, 240, COLORS["text_dim"] if pkt.status == "delivered" else COLORS["red"]),
            ]

            rx = rect.x + 8
            for text, w_col, col in row_data:
                txt_surf = font_d.render(text[:30], True, col)
                surface.blit(txt_surf, (rx, y))
                rx += w_col

            y += line_h
