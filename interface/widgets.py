"""Widget UI custom bergaya NOC: tombol, toggle, helper gambar."""
from typing import Callable

import pygame

import config
from config import COLORS


AUDIO_HOOK = None  # diisi Game: callable(nama_suara)
_FONT_CACHE: dict = {}


def _play(name: str) -> None:
    if AUDIO_HOOK:
        AUDIO_HOOK(name)


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _FONT_CACHE:
        path = config.ASSETS_DIR / "fonts" / "JetBrainsMono.ttf"
        if path.exists():
            font = pygame.font.Font(str(path), size)
            font.set_bold(bold)
        else:
            font = pygame.font.SysFont("consolas,dejavusansmono,couriernew,arial", size, bold=bold)
        _FONT_CACHE[key] = font
    return _FONT_CACHE[key]


def draw_text(surface, text, font, color, pos, anchor="topleft") -> pygame.Rect:
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    surface.blit(img, rect)
    return rect


def make_background(size: tuple[int, int]) -> pygame.Surface:
    """Gradient navy + grid tipis ala NOC."""
    w, h = size
    surf = pygame.Surface(size)
    top, bottom = COLORS["bg_dark"], (12, 24, 50)
    for y in range(h):
        t = y / max(1, h - 1)
        pygame.draw.line(surf, tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)), (0, y), (w, y))
    step = 48
    for x in range(0, w, step):
        pygame.draw.line(surf, COLORS["grid"], (x, 0), (x, h))
    for y in range(0, h, step):
        pygame.draw.line(surf, COLORS["grid"], (0, y), (w, y))
    return surf


class Button:
    def __init__(self, label: str, on_click: Callable[[], None], rect=(0, 0, 100, 40)) -> None:
        self.label = label
        self.on_click = on_click
        self.rect = pygame.Rect(rect)
        self.enabled = True
        self._hover = False
        self._pressed = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            now = self.rect.collidepoint(event.pos)
            if now and not self._hover:
                _play("hover")
            self._hover = now
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            fired = self._pressed and self.rect.collidepoint(event.pos)
            self._pressed = False
            if fired:
                _play("click")
                self.on_click()
                return True
        return False

    def _colors(self, focused: bool = False):
        if not self.enabled:
            return COLORS["bg_panel"], COLORS["gray"], COLORS["text_dim"]
        if self._pressed:
            return COLORS["blue"], COLORS["cyan"], COLORS["text"]
        if self._hover or focused:
            return COLORS["bg_panel_light"], COLORS["cyan"], COLORS["cyan"]
        return COLORS["bg_panel"], COLORS["blue"], COLORS["text"]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font | None = None, focused: bool = False) -> None:
        if font is None:
            font = get_font(14, True)
        fill, border, txt = self._colors(focused)
        pygame.draw.rect(surface, fill, self.rect, border_radius=8)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=8)
        draw_text(surface, self.label, font, txt, self.rect.center, "center")


class IconButton(Button):
    """Tombol dengan ikon opsional; label bisa disembunyikan (mode ikon saja)."""

    def __init__(self, label, on_click, icon=None, rect=(0, 0, 100, 34)) -> None:
        super().__init__(label, on_click, rect)
        self.icon = icon
        self.show_label = True

    def draw(self, surface, font=None, focused: bool = False) -> None:
        if font is None:
            font = get_font(14, True)
        fill, border, txt = self._colors(focused)
        pygame.draw.rect(surface, fill, self.rect, border_radius=7)
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=7)
        label = self.label if (self.show_label or not self.icon) else ""
        if self.icon and label:
            surface.blit(self.icon, self.icon.get_rect(midleft=(self.rect.x + 8, self.rect.centery)))
            draw_text(surface, label, font, txt, (self.rect.x + 12 + self.icon.get_width(), self.rect.centery), "midleft")
        elif self.icon:
            surface.blit(self.icon, self.icon.get_rect(center=self.rect.center))
        else:
            draw_text(surface, label, font, txt, self.rect.center, "center")


def fit_text(font: pygame.font.Font, text: str, max_w: int) -> str:
    """Potong teks dengan elipsis agar muat dalam max_w piksel."""
    if font.size(text)[0] <= max_w:
        return text
    while text and font.size(text + "...")[0] > max_w:
        text = text[:-1]
    return text + "..."


def wrap_text(font: pygame.font.Font, text: str, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if font.size(trial)[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def vertical_layout(count: int, area: pygame.Rect, max_h: int = 52, gap: int = 12) -> list[pygame.Rect]:
    """Susun `count` tombol vertikal dalam `area`; tinggi menyusut jika ruang sempit."""
    h = max(30, min(max_h, (area.height - gap * (count - 1)) // max(1, count)))
    total = h * count + gap * (count - 1)
    y0 = area.y + max(0, (area.height - total) // 2)
    return [pygame.Rect(area.x, y0 + i * (h + gap), area.width, h) for i in range(count)]
