"""Kelas utama: loop game, window, dan layanan bersama."""
import pygame

import config
from core.asset_manager import AssetManager
from core.event_manager import EventManager
from core.save_manager import SaveManager
from core.scene_manager import SceneManager


class Game:
    def __init__(self, db_path=None) -> None:
        pygame.init()
        pygame.display.set_caption(config.GAME_TITLE)
        self.save = SaveManager(db_path)
        self.events = EventManager()
        self.assets = AssetManager(self.save)
        self.scenes = SceneManager()
        self.running = False
        self.clock = pygame.time.Clock()
        self.screen = self._create_window(config.DEFAULT_SIZE)
        icon = self.assets.image("ui/app_icon.png")
        if icon:
            pygame.display.set_icon(icon)
        from interface import widgets
        widgets.AUDIO_HOOK = self.assets.play
        self.assets.apply_music()

    def _create_window(self, size) -> pygame.Surface:
        flags = pygame.RESIZABLE
        if self.save.get_bool("fullscreen"):
            flags = pygame.FULLSCREEN
            size = (0, 0)
        else:
            size = (max(size[0], config.MIN_SIZE[0]), max(size[1], config.MIN_SIZE[1]))
        return pygame.display.set_mode(size, flags)

    def set_option(self, key: str) -> None:
        self.save.toggle_bool(key)
        if key == "fullscreen":
            self.screen = self._create_window(config.DEFAULT_SIZE)
            self.scenes.resize(self.screen.get_size())
        if key == "music":
            self.assets.apply_music()
        self.events.emit("setting_changed", key=key)

    def quit(self) -> None:
        self.running = False

    def run(self, first_scene) -> None:
        self.scenes.clear_and_push(first_scene)
        self.running = True
        while self.running and self.scenes.current is not None:
            dt = self.clock.tick(config.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.VIDEORESIZE:
                    w, h = max(event.w, config.MIN_SIZE[0]), max(event.h, config.MIN_SIZE[1])
                    if (w, h) != (event.w, event.h) and not self.save.get_bool("fullscreen"):
                        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                    self.screen = pygame.display.get_surface()
                    self.scenes.resize(self.screen.get_size())
                elif self.scenes.current:
                    self.scenes.current.handle_event(event)
            if self.scenes.current:
                self.scenes.current.update(dt)
                self.scenes.current.draw(self.screen)
            if self.save.get_bool("show_fps"):
                from interface.widgets import draw_text, get_font
                draw_text(self.screen, f"{self.clock.get_fps():.0f} FPS", get_font(14), config.COLORS["green"], (8, 6))
            pygame.display.flip()
        self.save.close()
        pygame.quit()
