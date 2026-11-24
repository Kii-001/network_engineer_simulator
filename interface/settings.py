"""Layar pengaturan; nilai tersimpan permanen di SQLite."""
import pygame

from config import COLORS
from core.scene_manager import Scene
from interface.widgets import Button, draw_text, get_font, make_background, vertical_layout


class SettingsScene(Scene):
    OPTIONS = [
        ("music", "Background Music"),
        ("sfx", "Sound Effects"),
        ("fullscreen", "Fullscreen"),
        ("show_fps", "Tampilkan FPS"),
    ]

    def __init__(self, game) -> None:
        super().__init__(game)
        self.buttons: dict[str, Button] = {}
        for key, _ in self.OPTIONS:
            self.buttons[key] = Button("", lambda k=key: self._toggle(k))
        self.back = Button("< KEMBALI (Esc)", self.game.scenes.pop)
        self._bg = None
        self._refresh_labels()
        self.on_resize(game.screen.get_size())

    def _toggle(self, key: str) -> None:
        self.game.set_option(key)
        self._refresh_labels()

    def _refresh_labels(self) -> None:
        for key, label in self.OPTIONS:
            state = "ON " if self.game.save.get_bool(key) else "OFF"
            self.buttons[key].label = f"{label}: [{state}]"

    def on_enter(self) -> None:
        self._refresh_labels()

    def on_resize(self, size) -> None:
        self._bg = self.game.assets.image("backgrounds/dashboard_bg.png", size) or make_background(size)
        w, h = size
        area = pygame.Rect(0, int(h * 0.25), min(520, w - 40), int(h * 0.5))
        area.centerx = w // 2
        rects = vertical_layout(len(self.OPTIONS) + 1, area)
        for (key, _), r in zip(self.OPTIONS, rects):
            self.buttons[key].rect = r
        self.back.rect = rects[-1]

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.scenes.pop()
            return
        for b in list(self.buttons.values()) + [self.back]:
            if b.handle_event(event):
                break

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.blit(self._bg, (0, 0))
        draw_text(surface, "SETTINGS", get_font(38, True), COLORS["cyan"], (w // 2, int(h * 0.14)), "center")
        font = get_font(20, True)
        for b in list(self.buttons.values()) + [self.back]:
            b.draw(surface, font)
