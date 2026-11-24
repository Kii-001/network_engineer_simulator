"""Konfigurasi global Network Engineer Simulator."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "game.db"
ASSETS_DIR = BASE_DIR / "assets"

GAME_TITLE = "NETWORK ENGINEER SIMULATOR"
VERSION = "1.0.0 (Release - All Phases Complete)"

DEFAULT_SIZE = (1280, 720)
MIN_SIZE = (800, 500)
FPS = 60

# Tema NOC
COLORS = {
    "bg_dark": (8, 14, 28),
    "bg_panel": (16, 26, 46),
    "bg_panel_light": (24, 38, 66),
    "grid": (20, 34, 60),
    "blue": (41, 121, 255),
    "cyan": (0, 229, 255),
    "text": (222, 232, 248),
    "text_dim": (130, 150, 180),
    "green": (46, 214, 110),
    "red": (240, 66, 76),
    "yellow": (255, 196, 61),
    "gray": (60, 72, 92),
}

DEFAULT_SETTINGS = {
    "music": "1",
    "sfx": "1",
    "fullscreen": "0",
    "show_fps": "0",
}
