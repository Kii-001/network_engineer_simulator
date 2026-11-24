"""Layar sementara untuk mode yang dibangun pada fase berikutnya (berfungsi: info + kembali)."""
import pygame

from config import COLORS
from core.scene_manager import Scene
from interface.widgets import Button, draw_text, get_font, make_background


class PhaseInfoScene(Scene):
    def __init__(self, game, title: str, description: str, phase: str) -> None:
        super().__init__(game)
        self.title, self.description, self.phase = title, description, phase
        self.back = Button("< KEMBALI (Esc)", self.game.scenes.pop)
        self._bg = None
        self.on_resize(game.screen.get_size())

    def on_resize(self, size) -> None:
        self._bg = self.game.assets.image("backgrounds/dashboard_bg.png", size) or make_background(size)
        w, h = size
        self.back.rect = pygame.Rect(w // 2 - 130, int(h * 0.72), 260, 46)

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.scenes.pop()
            return
        self.back.handle_event(event)

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.blit(self._bg, (0, 0))
        panel = pygame.Rect(0, 0, min(760, w - 40), min(300, h - 40))
        panel.center = (w // 2, h // 2 - 20)
        pygame.draw.rect(surface, COLORS["bg_panel"], panel, border_radius=12)
        pygame.draw.rect(surface, COLORS["blue"], panel, 2, border_radius=12)
        draw_text(surface, self.title, get_font(34, True), COLORS["cyan"], (panel.centerx, panel.y + 55), "center")
        draw_text(surface, f"Tersedia pada {self.phase}", get_font(20), COLORS["yellow"], (panel.centerx, panel.y + 105), "center")
        words, line, y = self.description.split(), "", panel.y + 160
        font = get_font(18)
        for word in words:
            test = f"{line} {word}".strip()
            if font.size(test)[0] > panel.width - 60:
                draw_text(surface, line, font, COLORS["text"], (panel.centerx, y), "center")
                line, y = word, y + 26
            else:
                line = test
        draw_text(surface, line, font, COLORS["text"], (panel.centerx, y), "center")
        self.back.draw(surface, get_font(20, True))
