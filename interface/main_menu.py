"""Main Menu bergaya NOC."""
import math

import pygame

import config
from config import COLORS
from core.scene_manager import Scene
from interface.placeholder import PhaseInfoScene
from interface.settings import SettingsScene
from interface.workspace import WorkspaceScene
from interface.widgets import Button, draw_text, get_font, make_background, vertical_layout

MODES = [
    ("CAREER MODE", "Mulai sebagai Junior Network Technician dan naik menjadi Senior Network Engineer melalui 30 level.", "Phase 11"),
    ("FREE BUILD MODE", "Bangun topologi jaringan bebas tanpa batasan misi di Network Topology Editor.", "Phase 2"),
    ("CHALLENGE MODE", "Selesaikan tantangan jaringan dengan batas waktu dan anggaran.", "Phase 11"),
    ("TROUBLESHOOTING MODE", "Temukan dan perbaiki sumber gangguan pada jaringan yang rusak.", "Phase 11"),
    ("EXAM MODE", "Simulasi ujian praktik jaringan komputer.", "Phase 11"),
]


class MainMenuScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.buttons: list[Button] = []
        for title, desc, phase in MODES:
            self.buttons.append(Button(title, lambda t=title, d=desc, p=phase: self._open_mode(t, d, p)))
        self.buttons.append(Button("SETTINGS", lambda: self.game.scenes.push(SettingsScene(self.game))))
        self.buttons.append(Button("QUIT", self.game.quit))
        self.focus = 0
        self._bg = None
        self._logo = None
        self._t = 0.0
        self.on_resize(game.screen.get_size())

    def _open_mode(self, title: str, desc: str, phase: str) -> None:
        if title == "FREE BUILD MODE":
            self.game.scenes.push(WorkspaceScene(self.game, title, mode_type="free"))
        elif title == "CAREER MODE":
            from interface.dashboard import DashboardScene
            self.game.scenes.push(DashboardScene(self.game))
        elif title == "CHALLENGE MODE":
            from interface.challenge_hub import ChallengeModeScene
            self.game.scenes.push(ChallengeModeScene(self.game))
        elif title == "TROUBLESHOOTING MODE":
            from interface.troubleshooting_hub import TroubleshootingModeScene
            self.game.scenes.push(TroubleshootingModeScene(self.game))
        elif title == "EXAM MODE":
            from interface.exam_hub import ExamModeScene
            self.game.scenes.push(ExamModeScene(self.game))

    def on_resize(self, size) -> None:
        self._bg = self.game.assets.image("backgrounds/menu_bg.png", size) or make_background(size)
        w, h = size
        self._logo = None
        logo = self.game.assets.image("ui/logo.png")
        if logo:
            k = min(720 / logo.get_width(), w * 0.7 / logo.get_width(), h * 0.15 / logo.get_height())
            self._logo = pygame.transform.smoothscale(logo, (int(logo.get_width() * k), int(logo.get_height() * k)))
        area = pygame.Rect(0, int(h * 0.30), min(440, w - 40), int(h * 0.62))
        area.centerx = w // 2
        for b, r in zip(self.buttons, vertical_layout(len(self.buttons), area, max_h=50, gap=10)):
            b.rect = r

    def update(self, dt: float) -> None:
        self._t += dt

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.focus = (self.focus + 1) % len(self.buttons)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.focus = (self.focus - 1) % len(self.buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.buttons[self.focus].on_click()
            return
        for i, b in enumerate(self.buttons):
            if event.type == pygame.MOUSEMOTION and b.rect.collidepoint(event.pos):
                self.focus = i
            if b.handle_event(event):
                break

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.blit(self._bg, (0, 0))
        title_size = max(24, min(54, w // 22))
        if self._logo:
            surface.blit(self._logo, self._logo.get_rect(center=(w // 2, int(h * 0.11))))
        else:
            draw_text(surface, config.GAME_TITLE, get_font(title_size, True), COLORS["cyan"], (w // 2, int(h * 0.11)), "center")
        draw_text(surface, "Build. Configure. Troubleshoot.", get_font(max(14, int(title_size / 2.6))), COLORS["text_dim"], (w // 2, int(h * 0.19)), "center")
        # indikator online berkedip
        pulse = 0.5 + 0.5 * math.sin(self._t * 3)
        dot = tuple(int(c * (0.5 + 0.5 * pulse)) for c in COLORS["green"])
        pygame.draw.circle(surface, dot, (24, h - 24), 6)
        profile = self.game.save.get_profile()
        draw_text(surface, f"ONLINE  |  {profile['name']}  |  {profile['rank']}", get_font(15), COLORS["text_dim"], (38, h - 24), "midleft")
        draw_text(surface, f"v{config.VERSION}", get_font(15), COLORS["text_dim"], (w - 16, h - 24), "midright")
        font = get_font(20, True)
        for i, b in enumerate(self.buttons):
            b.draw(surface, font, focused=(i == self.focus))
