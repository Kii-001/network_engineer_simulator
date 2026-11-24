"""Scene dasar dan manajer scene berbasis stack."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from core.game import Game


class Scene:
    """Kelas dasar semua layar. UI hanya menggambar & menerima input."""

    def __init__(self, game: "Game") -> None:
        self.game = game

    def on_enter(self) -> None: ...
    def on_exit(self) -> None: ...
    def on_resize(self, size: tuple[int, int]) -> None: ...
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...
    def draw(self, surface: pygame.Surface) -> None: ...


class SceneManager:
    def __init__(self) -> None:
        self._stack: list[Scene] = []

    @property
    def current(self) -> Scene | None:
        return self._stack[-1] if self._stack else None

    def push(self, scene: Scene) -> None:
        self._stack.append(scene)
        scene.on_enter()

    def pop(self) -> None:
        if self._stack:
            self._stack.pop().on_exit()

    def replace(self, scene: Scene) -> None:
        self.pop()
        self.push(scene)

    def clear_and_push(self, scene: Scene) -> None:
        while self._stack:
            self.pop()
        self.push(scene)

    def resize(self, size: tuple[int, int]) -> None:
        for scene in self._stack:
            scene.on_resize(size)

    def __len__(self) -> int:
        return len(self._stack)
