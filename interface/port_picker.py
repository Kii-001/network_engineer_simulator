"""Popup modal untuk memilih port perangkat saat memasang kabel."""
from __future__ import annotations

import pygame

from config import COLORS
from interface.widgets import draw_text, fit_text, get_font


class PortPicker:
    ROW_H, W, MAX_ROWS = 26, 280, 9

    def __init__(self, entries: list[dict], anchor, bounds: pygame.Rect, title: str, on_choose) -> None:
        self.entries, self.title, self.on_choose = entries, title, on_choose
        self.scroll, self.hover, self.closed = 0, None, False
        rows = min(len(entries), self.MAX_ROWS)
        h = 36 + rows * self.ROW_H + 8 + (16 if len(entries) > rows else 0)
        x = min(max(bounds.left + 4, anchor[0] + 20), max(bounds.left + 4, bounds.right - self.W - 4))
        y = min(max(bounds.top + 4, anchor[1] - h // 2), max(bounds.top + 4, bounds.bottom - h - 4))
        self.rect = pygame.Rect(x, y, self.W, h)
        self.rows = rows

    def _row_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(self.rect.x + 6, self.rect.y + 32 + (i - self.scroll) * self.ROW_H, self.rect.width - 12, self.ROW_H - 2)

    def _index_at(self, pos):
        for i in range(self.scroll, min(len(self.entries), self.scroll + self.rows)):
            if self._row_rect(i).collidepoint(pos):
                return i
        return None

    def handle_event(self, event) -> bool:
        """Modal: selalu mengonsumsi event input sampai ditutup."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.closed = True
            return True
        if event.type == pygame.MOUSEMOTION:
            self.hover = self._index_at(event.pos) if self.rect.collidepoint(event.pos) else None
            return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - event.y, max(0, len(self.entries) - self.rows)))
            return True
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                i = self._index_at(event.pos)
                if i is not None and self.entries[i]["enabled"]:
                    self.closed = True
                    self.on_choose(self.entries[i]["name"])
            else:
                self.closed = True
            return True
        return event.type == pygame.MOUSEBUTTONUP

    def draw(self, surface, assets) -> None:
        pygame.draw.rect(surface, COLORS["bg_panel"], self.rect, border_radius=10)
        pygame.draw.rect(surface, COLORS["cyan"], self.rect, 2, border_radius=10)
        draw_text(surface, fit_text(get_font(14, True), self.title, self.W - 16), get_font(14, True), COLORS["cyan"], (self.rect.x + 10, self.rect.y + 9))
        font, small = get_font(13), get_font(12)
        for i in range(self.scroll, min(len(self.entries), self.scroll + self.rows)):
            e, rr = self.entries[i], self._row_rect(i)
            if i == self.hover and e["enabled"]:
                pygame.draw.rect(surface, COLORS["bg_panel_light"], rr, border_radius=6)
                pygame.draw.rect(surface, COLORS["cyan"], rr, 1, border_radius=6)
            led = assets.image(f"ui/led_{ {'off': 'off', 'up': 'green', 'down': 'red'}[e['state']] }.png")
            if led:
                surface.blit(led, led.get_rect(midleft=(rr.x + 4, rr.centery)))
            col = COLORS["text"] if e["enabled"] else COLORS["gray"]
            draw_text(surface, f"{e['short']} [{e['kind']}]", font, col, (rr.x + 26, rr.centery), "midleft")
            if e["note"]:
                draw_text(surface, e["note"], small, COLORS["red"] if e["note"] == "terpakai" else COLORS["text_dim"], (rr.right - 6, rr.centery), "midright")
        if len(self.entries) > self.rows:
            more = len(self.entries) - self.rows
            draw_text(surface, f"scroll mouse: +{more} port lagi", small, COLORS["text_dim"], (self.rect.centerx, self.rect.bottom - 14), "center")
