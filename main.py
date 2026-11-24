"""Entry point: python main.py"""
from core.game import Game
from interface.main_menu import MainMenuScene


def main() -> None:
    game = Game()
    game.run(MainMenuScene(game))


if __name__ == "__main__":
    main()
