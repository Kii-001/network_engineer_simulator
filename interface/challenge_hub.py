"""Challenge Mode Hub: Tantangan kecepatan (speedrun) dan anggaran jaringan berbatas waktu."""
from __future__ import annotations

import json
from pathlib import Path
import pygame
import config
from config import COLORS
from core.scene_manager import Scene
from interface.widgets import Button, draw_text, get_font


class ChallengeModeScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        path = config.BASE_DIR / "data" / "challenges.json"
        with open(path, encoding="utf-8") as f:
            self.challenges = json.load(f)
        self.profile = game.save.get_profile()
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
        cols = max(1, min(2, (w - 60) // 420))
        card_w = (w - 60 - (cols - 1) * 20) // cols
        card_h = 130
        start_y = 120

        for i, c in enumerate(self.challenges):
            col = i % cols
            row = i // cols
            rx = 30 + col * (card_w + 20)
            ry = start_y + row * (card_h + 16)

            self.cards.append({
                "data": c,
                "base_rect": pygame.Rect(rx, ry, card_w, card_h),
            })

        total_rows = (len(self.challenges) + cols - 1) // cols
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
                    c = item["data"]
                    self.game.scenes.push(WorkspaceScene(
                        self.game,
                        title=f"CHALLENGE: {c['title'].upper()}",
                        mission_id=None,
                        mode_type="challenge"
                    ))
                    break

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.fill(COLORS["bg_dark"])

        # Header Bar
        pygame.draw.rect(surface, COLORS["bg_panel"], pygame.Rect(0, 0, w, 100))
        pygame.draw.line(surface, COLORS["yellow"], (0, 100), (w, 100), 2)

        self.btn_back.draw(surface, get_font(13, True))

        # Title
        f_title = get_font(20, True)
        f_sub = get_font(13)
        draw_text(surface, "CHALLENGE MODE: SPEED & BUDGET NETWORK TRIALS", f_title, COLORS["yellow"], (220, 16))
        draw_text(surface, "Selesaikan tantangan jaringan dengan batas waktu ketat & raih Medali Emas, Perak, Perunggu!", f_sub, COLORS["text_dim"], (220, 48))

        # Cards
        mouse = pygame.mouse.get_pos()
        for item in self.cards:
            r = item["base_rect"].move(0, -self.scroll_y)
            if r.bottom < 100 or r.top > h:
                continue

            hover = r.collidepoint(mouse)
            bg_col = COLORS["bg_panel_light"] if hover else COLORS["bg_panel"]
            border_col = COLORS["yellow"] if hover else COLORS["gray"]

            pygame.draw.rect(surface, bg_col, r, border_radius=8)
            pygame.draw.rect(surface, border_col, r, 2 if hover else 1, border_radius=8)

            c = item["data"]
            diff_col = COLORS["red"] if c["difficulty"] in ("Expert", "Master") else (COLORS["yellow"] if c["difficulty"] == "Hard" else COLORS["green"])
            
            draw_text(surface, f"#{c['id']} {c['title']}", get_font(15, True), COLORS["text"], (r.x + 14, r.y + 12))
            draw_text(surface, f"[{c['difficulty'].upper()}]", get_font(11, True), diff_col, (r.right - 80, r.y + 14))

            desc_lines = c["description"]
            draw_text(surface, desc_lines[:75] + ("..." if len(desc_lines) > 75 else ""), get_font(12), COLORS["text_dim"], (r.x + 14, r.y + 40))

            # Target waktu & anggaran
            draw_text(surface, f"Batas Waktu: {c['time_limit']}s   |   Anggaran: ${c['budget']}", get_font(12, True), COLORS["cyan"], (r.x + 14, r.y + 70))
            draw_text(surface, f"Target Emas: <={c['gold_time']}s   |   Perak: <={c['silver_time']}s   |   Perunggu: <={c['bronze_time']}s", get_font(11), COLORS["yellow"], (r.x + 14, r.y + 96))
