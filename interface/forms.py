"""Komponen form: TextField dan kelas dasar Dialog modal."""
from __future__ import annotations

import pygame

from config import COLORS
from interface.widgets import draw_text, get_font

IP_CHARS = set("0123456789.")
MASK_CHARS = set("0123456789./")


class TextField:
    def __init__(self, text: str = "", allowed=None, max_len: int = 18, placeholder: str = "") -> None:
        self.text, self.allowed, self.max_len, self.placeholder = text, allowed, max_len, placeholder
        self.rect = pygame.Rect(0, 0, 120, 30)
        self.focused = False
        self.error = False
        self.cursor = len(text)

    def set_text(self, text: str) -> None:
        self.text, self.cursor = text, len(text)

    def click(self, pos) -> bool:
        if self.rect.collidepoint(pos):
            self.cursor = len(self.text)
            return True
        return False

    def handle_key(self, event) -> bool:
        k, c = event.key, self.cursor
        if k == pygame.K_BACKSPACE:
            if c > 0:
                self.text, self.cursor = self.text[:c - 1] + self.text[c:], c - 1
        elif k == pygame.K_DELETE:
            self.text = self.text[:c] + self.text[c + 1:]
        elif k == pygame.K_LEFT:
            self.cursor = max(0, c - 1)
        elif k == pygame.K_RIGHT:
            self.cursor = min(len(self.text), c + 1)
        elif k == pygame.K_HOME:
            self.cursor = 0
        elif k == pygame.K_END:
            self.cursor = len(self.text)
        elif event.unicode and event.unicode.isprintable() and len(self.text) < self.max_len \
                and (self.allowed is None or event.unicode in self.allowed):
            self.text, self.cursor = self.text[:c] + event.unicode + self.text[c:], c + 1
        else:
            return False
        self.error = False
        return True

    def draw(self, surface, font, t: float) -> None:
        border = COLORS["red"] if self.error else COLORS["cyan"] if self.focused else COLORS["blue"]
        pygame.draw.rect(surface, COLORS["bg_dark"], self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=6)
        if self.text or self.focused:
            draw_text(surface, self.text, font, COLORS["text"], (self.rect.x + 8, self.rect.centery), "midleft")
            if self.focused and int(t * 2) % 2 == 0:
                cx = self.rect.x + 8 + font.size(self.text[:self.cursor])[0]
                pygame.draw.line(surface, COLORS["cyan"], (cx, self.rect.y + 6), (cx, self.rect.bottom - 6), 2)
        else:
            draw_text(surface, self.placeholder, font, COLORS["gray"], (self.rect.x + 8, self.rect.centery), "midleft")


class Dialog:
    """Dialog modal: mengonsumsi semua input sampai `closed` bernilai True."""

    def __init__(self, workspace) -> None:
        self.ws = workspace
        self.closed = False
        self.rect = pygame.Rect(0, 0, 400, 300)
        self.t = 0.0
        self._dim = None

    def layout(self, size) -> None:
        self._dim = pygame.Surface(size, pygame.SRCALPHA)
        self._dim.fill((0, 0, 0, 160))

    def update(self, dt: float) -> None:
        self.t += dt

    def handle_event(self, event) -> bool:
        return True

    def draw_frame(self, surface, title: str) -> None:
        if self._dim is None or self._dim.get_size() != surface.get_size():
            self.layout(surface.get_size())
        surface.blit(self._dim, (0, 0))
        pygame.draw.rect(surface, COLORS["bg_panel"], self.rect, border_radius=12)
        pygame.draw.rect(surface, COLORS["cyan"], self.rect, 2, border_radius=12)
        draw_text(surface, title, get_font(17, True), COLORS["cyan"], (self.rect.x + 20, self.rect.y + 16))
        pygame.draw.line(surface, COLORS["blue"], (self.rect.x + 14, self.rect.y + 44), (self.rect.right - 14, self.rect.y + 44))
