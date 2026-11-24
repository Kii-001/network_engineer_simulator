"""Exam Hub: Simulasi Ujian Sertifikasi Praktik Jaringan Komputer Profesional."""
from __future__ import annotations

import json
from pathlib import Path
import pygame
import config
from config import COLORS
from core.scene_manager import Scene
from interface.widgets import Button, draw_text, get_font


class ExamModeScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        path = config.BASE_DIR / "data" / "exams.json"
        with open(path, encoding="utf-8") as f:
            self.exams = json.load(f)
        self.btn_back = Button("KEMBALI KE MENU", self._go_back)
        self.scroll_y = 0
        self.max_scroll = 0
        self.cards: list[dict] = []
        self.on_resize(game.screen.get_size())

    def _go_back(self) -> None:
        from interface.main_menu import MainMenuScene
        self.game.scenes.clear_and_push(MainMenuScene(self.game))

    def on_resize(self, size) -> None:
        w, h = size
        self.btn_back.rect = pygame.Rect(20, 16, 180, 36)
        self._build_cards(w, h)

    def _build_cards(self, w: int, h: int) -> None:
        self.cards.clear()
        cols = max(1, min(2, (w - 60) // 440))
        card_w = (w - 60 - (cols - 1) * 20) // cols
        card_h = 145
        start_y = 120

        for i, ex in enumerate(self.exams):
            col = i % cols
            row = i // cols
            rx = 30 + col * (card_w + 20)
            ry = start_y + row * (card_h + 16)

            self.cards.append({
                "data": ex,
                "base_rect": pygame.Rect(rx, ry, card_w, card_h),
            })

        total_rows = (len(self.exams) + cols - 1) // cols
        total_h = start_y + total_rows * (card_h + 16) + 40
        self.max_scroll = max(0, total_h - h)

    def handle_event(self, event) -> None:
        if self.btn_back.handle_event(event):
            return

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * 36))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for item in self.cards:
                r = item["base_rect"].move(0, -self.scroll_y)
                if r.collidepoint(mx, my):
                    from interface.workspace import WorkspaceScene
                    ex = item["data"]
                    self.game.scenes.push(WorkspaceScene(
                        self.game,
                        title=f"UJIAN {ex['code']}: {ex['title'].upper()}",
                        mission_id=None,
                        mode_type="exam"
                    ))
                    break

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.fill(COLORS["bg_dark"])

        # Header Bar
        pygame.draw.rect(surface, COLORS["bg_panel"], pygame.Rect(0, 0, w, 100))
        pygame.draw.line(surface, COLORS["cyan"], (0, 100), (w, 100), 2)

        self.btn_back.draw(surface, get_font(13, True))

        # Title
        f_title = get_font(20, True)
        f_sub = get_font(13)
        draw_text(surface, "CERTIFICATION EXAM CENTER: UJIAN PRAKTIK RESMI", f_title, COLORS["cyan"], (220, 16))
        draw_text(surface, "Uji kompetensi teknis praktis Anda di bawah standar sertifikasi industri. Nilai kelulusan minimal 80%.", f_sub, COLORS["text_dim"], (220, 48))

        # Cards
        mouse = pygame.mouse.get_pos()
        for item in self.cards:
            r = item["base_rect"].move(0, -self.scroll_y)
            if r.bottom < 100 or r.top > h:
                continue

            hover = r.collidepoint(mouse)
            bg_col = COLORS["bg_panel_light"] if hover else COLORS["bg_panel"]
            border_col = COLORS["cyan"] if hover else COLORS["gray"]

            pygame.draw.rect(surface, bg_col, r, border_radius=8)
            pygame.draw.rect(surface, border_col, r, 2 if hover else 1, border_radius=8)

            ex = item["data"]
            tier_col = COLORS["cyan"] if ex["tier"] == "Associate" else (COLORS["green"] if ex["tier"] == "Professional" else (COLORS["yellow"] if ex["tier"] == "Senior" else COLORS["red"]))

            # Exam code & Tier
            draw_text(surface, f"KODE: {ex['code']}", get_font(12, True), COLORS["text_dim"], (r.x + 14, r.y + 10))
            draw_text(surface, f"[{ex['tier'].upper()}]", get_font(11, True), tier_col, (r.right - 110, r.y + 10))

            # Judul Ujian
            draw_text(surface, ex["title"], get_font(15, True), COLORS["text"], (r.x + 14, r.y + 30))

            # Deskripsi
            desc = ex["description"]
            draw_text(surface, desc[:90] + ("..." if len(desc) > 90 else ""), get_font(11), COLORS["text_dim"], (r.x + 14, r.y + 56))

            # Syarat Kelulusan & Reward
            draw_text(surface, f"Passing Score: {ex['passing_score']}%   |   Durasi: {ex['time_limit'] // 60} Menit", get_font(12, True), COLORS["yellow"], (r.x + 14, r.y + 86))
            draw_text(surface, f"Lencana: {ex['badge']}", get_font(11, True), COLORS["green"], (r.x + 14, r.y + 112))

            # Action pill
            action_rect = pygame.Rect(r.right - 145, r.bottom - 32, 130, 24)
            pygame.draw.rect(surface, COLORS["blue"] if hover else COLORS["bg_panel_light"], action_rect, border_radius=4)
            draw_text(surface, "IKUTI UJIAN ->", get_font(10, True), COLORS["cyan"] if hover else COLORS["text"], action_rect.center, "center")
