"""Interactive terminal entry point for selecting a Language Lab language."""

import curses
import urllib.error

from scrape_language_selection import get_language_options


MENU_PROMPT = "Select a language (Up/Down to move, Enter to choose, q to quit)"


def _selection_screen(screen, options: list[str]) -> str:
    """Display a scrolling terminal menu and return the selected option."""
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    screen.keypad(True)
    selected_index = 0
    first_visible_index = 0

    while True:
        height, width = screen.getmaxyx()
        visible_rows = max(1, height - 2)

        if selected_index < first_visible_index:
            first_visible_index = selected_index
        elif selected_index >= first_visible_index + visible_rows:
            first_visible_index = selected_index - visible_rows + 1

        screen.erase()
        screen.addnstr(0, 0, MENU_PROMPT, max(1, width - 1), curses.A_BOLD)

        last_visible_index = min(
            len(options),
            first_visible_index + visible_rows,
        )
        for row, option_index in enumerate(
            range(first_visible_index, last_visible_index),
            start=2,
        ):
            marker = "> " if option_index == selected_index else "  "
            style = (
                curses.A_REVERSE
                if option_index == selected_index
                else curses.A_NORMAL
            )
            screen.addnstr(
                row,
                0,
                f"{marker}{options[option_index]}",
                max(1, width - 1),
                style,
            )

        screen.refresh()
        key = screen.getch()

        if key in (curses.KEY_UP, ord("k")):
            selected_index = (selected_index - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord("j")):
            selected_index = (selected_index + 1) % len(options)
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[selected_index]
        elif key in (ord("q"), 27):
            raise KeyboardInterrupt


def select_language(options: list[str]) -> str:
    """Open the terminal menu for a non-empty list of language options."""
    if not options:
        raise ValueError("No language options are available.")

    return curses.wrapper(_selection_screen, options)


def main() -> None:
    """Fetch languages, prompt for a selection, and display the result."""
    try:
        languages = get_language_options()
        selected_language = select_language(languages)
    except urllib.error.URLError as error:
        raise SystemExit(
            f"Unable to download language options: {error.reason}"
        ) from error
    except ValueError as error:
        raise SystemExit(str(error)) from error
    except KeyboardInterrupt:
        print("\nSelection cancelled.")
        return

    print(f"\nSelected language: {selected_language}")


if __name__ == "__main__":
    main()
