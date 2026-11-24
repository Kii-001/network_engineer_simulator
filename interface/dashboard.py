"""Career Dashboard: Progres karier, peringkat teknisi, dan seleksi 30 level misi."""
from __future__ import annotations

import pygame
from config import COLORS
from core.scene_manager import Scene
from interface.widgets import Button, draw_text, get_font
from missions.mission_manager import MissionManager


class DashboardScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.mgr = MissionManager()
        self.profile = game.save.get_profile()
        self.stars_map = game.save.get_mission_stars_map()
        self.scroll_y = 0
        self.max_scroll = 0
        self.cards: list[dict] = []
        self.btn_back = Button("KEMBALI KE MENU", self._go_back)
        self._bg = None
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
        cols = max(1, min(4, (w - 60) // 270))
        card_w = (w - 60 - (cols - 1) * 16) // cols
        card_h = 100
        start_y = 120

        # Misi pertama selalu terbuka; misi berikutnya terbuka jika misi sebelumnya selesai (bintang >= 1)
        for i, m in enumerate(self.mgr.missions):
            mid = m["id"]
            prev_stars = self.stars_map.get(mid - 1, 0) if mid > 1 else 1
            unlocked = (mid == 1) or (prev_stars > 0)
            stars = self.stars_map.get(mid, 0)

            col = i % cols
            row = i // cols
            rx = 30 + col * (card_w + 16)
            ry = start_y + row * (card_h + 16)

            self.cards.append({
                "mission": m,
                "unlocked": unlocked,
                "stars": stars,
                "base_rect": pygame.Rect(rx, ry, card_w, card_h),
            })

        total_rows = (len(self.mgr.missions) + cols - 1) // cols
        total_h = start_y + total_rows * (card_h + 16) + 40
        self.max_scroll = max(0, total_h - h)

    def handle_event(self, event) -> None:
        if self.btn_back.handle_event(event):
            return

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - event.y * 36))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for c in self.cards:
                r = c["base_rect"].move(0, -self.scroll_y)
                if r.collidepoint(mx, my):
                    if c["unlocked"]:
                        from interface.workspace import WorkspaceScene
                        self.game.scenes.push(WorkspaceScene(self.game, title=f"LEVEL {c['mission']['id']}: {c['mission']['title']}", mission_id=c['mission']['id']))
                    else:
                        self.game.assets.play("error")
                    break

    def draw(self, surface) -> None:
        w, h = surface.get_size()
        surface.fill(COLORS["bg_dark"])

        # Header Dashboard
        pygame.draw.rect(surface, COLORS["bg_panel"], pygame.Rect(0, 0, w, 100))
        pygame.draw.line(surface, COLORS["blue"], (0, 100), (w, 100), 2)

        self.btn_back.draw(surface, get_font(13, True))

        # Profile info
        f_title = get_font(20, True)
        f_sub = get_font(13)
        draw_text(surface, f"CAREER DASHBOARD: {self.profile['name'].upper()}", f_title, COLORS["cyan"], (220, 16))
        draw_text(surface, f"Pangkat: {self.profile['rank']}   |   XP: {self.profile['xp']}   |   Koin: ${self.profile['coins']}", f_sub, COLORS["text"], (220, 48))

        # Total Stars
        total_stars = sum(self.stars_map.values())
        star_ico = self.game.assets.image("icons/star.png", (20, 20))
        if star_ico:
            surface.blit(star_ico, (w - 180, 24))
        draw_text(surface, f"Stars: {total_stars} / 90", get_font(16, True), COLORS["yellow"], (w - 150, 24))

        # Level Cards
        star_img = self.game.assets.image("icons/star.png", (16, 16))
        star_empty = self.game.assets.image("icons/star_empty.png", (16, 16))
        lock_img = self.game.assets.image("icons/lock.png", (20, 20))

        mouse = pygame.mouse.get_pos()
        for c in self.cards:
            r = c["base_rect"].move(0, -self.scroll_y)
            if r.bottom < 100 or r.top > h:
                continue

            hover = r.collidepoint(mouse) and c["unlocked"]
            bg_col = COLORS["bg_panel_light"] if hover else COLORS["bg_panel"]
            border_col = COLORS["cyan"] if hover else (COLORS["blue"] if c["unlocked"] else COLORS["gray"])

            pygame.draw.rect(surface, bg_col, r, border_radius=6)
            pygame.draw.rect(surface, border_col, r, 2 if hover else 1, border_radius=6)

            m = c["mission"]
            f_num = get_font(14, True)
            f_cat = get_font(11)
            
            # Judul Level
            title_col = COLORS["cyan"] if c["unlocked"] else COLORS["text_dim"]
            draw_text(surface, f"LVL {m['id']}: {m['title']}", f_num, title_col, (r.x + 12, r.y + 10))
            draw_text(surface, m["category"], f_cat, COLORS["text_dim"], (r.x + 12, r.y + 34))

            # Bintang / Gembok
            if not c["unlocked"]:
                if lock_img:
                    surface.blit(lock_img, (r.right - 32, r.y + 12))
                else:
                    draw_text(surface, "LOCKED", f_cat, COLORS["red"], (r.right - 60, r.y + 14))
            else:
                sx = r.right - 62
                for s in range(3):
                    img = star_img if s < c["stars"] else star_empty
                    if img:
                        surface.blit(img, (sx + s * 18, r.y + 12))

            # Info reward & budget
            draw_text(surface, f"Budget: ${m['budget']}   XP: +{m['xp_reward']}", f_cat, COLORS["green"] if c["unlocked"] else COLORS["text_dim"], (r.x + 12, r.y + 68))
