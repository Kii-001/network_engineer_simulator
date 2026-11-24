"""Laporan evaluasi misi: Penilaian teknis, skor bintang, reward, dan feedback solusi."""
from __future__ import annotations

import pygame
from config import COLORS
from core.scene_manager import Scene
from interface.widgets import Button, draw_text, get_font


class MissionReportScene(Scene):
    def __init__(self, game, result: dict, on_continue=None) -> None:
        super().__init__(game)
        self.result = result
        self.on_continue = on_continue
        self.btn_ok = Button("LANJUTKAN", self._finish)
        self.on_resize(game.screen.get_size())

    def _finish(self) -> None:
        if self.on_continue:
            self.on_continue()
        else:
            from interface.dashboard import DashboardScene
            self.game.scenes.clear_and_push(DashboardScene(self.game))

    def on_resize(self, size) -> None:
        w, h = size
        dialog_w = min(680, w - 40)
        dialog_h = min(520, h - 40)
        self.rect = pygame.Rect((w - dialog_w) // 2, (h - dialog_h) // 2, dialog_w, dialog_h)
        self.btn_ok.rect = pygame.Rect(self.rect.centerx - 90, self.rect.bottom - 54, 180, 40)

    def handle_event(self, event) -> None:
        if self.btn_ok.handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            self._finish()

    def draw(self, surface) -> None:
        # Dim background
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        surface.blit(dim, (0, 0))

        # Dialog Box
        pygame.draw.rect(surface, COLORS["bg_panel"], self.rect, border_radius=8)
        border_col = COLORS["green"] if self.result["success"] else COLORS["red"]
        pygame.draw.rect(surface, border_col, self.rect, 2, border_radius=8)

        # Header Title
        f_title = get_font(22, True)
        title_text = "MISI SELESAI (SUKSES!)" if self.result["success"] else "EVALUASI MISI: BELUM LENGKAP"
        draw_text(surface, title_text, f_title, border_col, (self.rect.x + 24, self.rect.y + 20))

        f_sub = get_font(14)
        draw_text(surface, f"Level: {self.result['title']}   |   Waktu: {int(self.result['elapsed_seconds'])} detik", f_sub, COLORS["text_dim"], (self.rect.x + 24, self.rect.y + 54))

        # Score & Stars
        score_box = pygame.Rect(self.rect.x + 24, self.rect.y + 84, self.rect.width - 48, 64)
        pygame.draw.rect(surface, COLORS["bg_panel_light"], score_box, border_radius=6)

        draw_text(surface, f"SKOR: {self.result['score']} / 100", get_font(18, True), COLORS["cyan"], (score_box.x + 16, score_box.y + 12))
        
        # Bintang
        star_img = self.game.assets.image("icons/star.png", (24, 24))
        star_empty = self.game.assets.image("icons/star_empty.png", (24, 24))
        sx = score_box.right - 100
        for s in range(3):
            img = star_img if s < self.result["stars"] else star_empty
            if img:
                surface.blit(img, (sx + s * 28, score_box.y + 18))

        # Rewards
        draw_text(surface, f"Reward: +{self.result['xp']} XP   |   +${self.result['coins']} Koin", f_sub, COLORS["green"], (score_box.x + 16, score_box.y + 38))

        # Feedback & Objectives list
        y = self.rect.y + 164
        f_sec = get_font(14, True)
        f_item = get_font(12)

        if self.result["passed_objectives"]:
            draw_text(surface, "Sasaran Berhasil:", f_sec, COLORS["green"], (self.rect.x + 24, y))
            y += 22
            for obj in self.result["passed_objectives"][:4]:
                draw_text(surface, f"  [v] {obj}", f_item, COLORS["text"], (self.rect.x + 24, y))
                y += 18

        if self.result["errors"]:
            y += 8
            draw_text(surface, "Catatan Evaluasi / Kesalahan:", f_sec, COLORS["red"], (self.rect.x + 24, y))
            y += 22
            for err in self.result["errors"][:5]:
                draw_text(surface, f"  [!] {err}", f_item, COLORS["yellow"], (self.rect.x + 24, y))
                y += 18

        self.btn_ok.draw(surface, get_font(14, True))
