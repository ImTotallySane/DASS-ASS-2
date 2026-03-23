"""Entry point for the MoneyPoly whitebox example.

This module provides a simple command-line launcher that reads player
names, constructs a `Game`, and starts the game loop.
"""

from moneypoly.game import Game


def get_player_names():
    """Prompt the user for comma-separated player names and return a list.

    The function strips whitespace and ignores empty entries. It does not
    validate the minimum number of players; validation is performed by the
    caller.
    """
    print("Enter player names separated by commas (minimum 2 players):")
    raw = input("> ").strip()
    names = [n.strip() for n in raw.split(",") if n.strip()]
    return names


def main():
    """Run the MoneyPoly game from the command line.

    This function collects player names, constructs a `Game` instance, and
    starts the main loop. It handles keyboard interrupts and setup errors
    gracefully.
    """
    names = get_player_names()
    try:
        game = Game(names)
        game.run()
    except KeyboardInterrupt:
        print("\n\n  Game interrupted. Goodbye!")
    except ValueError as exc:
        print(f"Setup error: {exc}")


if __name__ == "__main__":
    main()
