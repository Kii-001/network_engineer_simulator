"""Pemuat asset (gambar, suara, musik) dengan cache dan fallback aman."""
import pygame

import config


class AssetManager:
    def __init__(self, save) -> None:
        self.save = save
        self._images: dict = {}
        self._sounds: dict = {}
        self.audio_ok = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.audio_ok = True
        except pygame.error:
            self.audio_ok = False  # tidak ada perangkat audio; game tetap jalan

    # --- gambar ---
    def image(self, rel: str, size=None):
        """Kembalikan Surface atau None bila file tidak ada. `rel` relatif ke assets/images."""
        key = (rel, size)
        if key not in self._images:
            path = config.ASSETS_DIR / "images" / rel
            img = None
            if path.exists():
                img = pygame.image.load(str(path))
                img = img.convert_alpha() if pygame.display.get_surface() else img
                if size:
                    img = pygame.transform.smoothscale(img, size)
            self._images[key] = img
        return self._images[key]

    def device_icon(self, device_type: str, small: bool = False):
        return self.image(f"devices/{device_type}{'_small' if small else ''}.png")

    # --- suara ---
    def sound(self, name: str):
        if not self.audio_ok:
            return None
        if name not in self._sounds:
            path = config.ASSETS_DIR / "sounds" / f"{name}.wav"
            self._sounds[name] = pygame.mixer.Sound(str(path)) if path.exists() else None
        return self._sounds[name]

    def play(self, name: str) -> None:
        if self.save.get_bool("sfx"):
            snd = self.sound(name)
            if snd:
                snd.set_volume(0.6)
                snd.play()

    def apply_music(self) -> None:
        """Sinkronkan musik latar dengan pengaturan Music."""
        if not self.audio_ok:
            return
        if self.save.get_bool("music"):
            path = config.ASSETS_DIR / "sounds" / "music" / "bgm_noc.wav"
            if path.exists() and not pygame.mixer.music.get_busy():
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.set_volume(0.35)
                pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.stop()
