"""Interactive terminal entry point for selecting a language and book."""

import curses
from pathlib import Path
import urllib.error

from create_anki_deck import TTSAudioMode, create_anki_package, package_filename
from language_lab_api import MenuOption
from progress_reporting import TerminalProgress
from scrape_flashcards import get_flashcards_for_book
from scrape_language_menus import get_book_options, get_language_options


LANGUAGE_PROMPT = (
    "Select a language (Up/Down to move, Enter to choose, q to quit)"
)
BOOK_PROMPT_TEMPLATE = (
    "Select a book for {language} "
    "(Up/Down to move, Enter to choose, q to quit)"
)
RETURN_TO_LANGUAGES = "Return to language selection"
TTS_PROMPT = "Which cards would you like to have TTS with?"


def _selection_screen(screen, options: list[str], prompt: str) -> int:
    """Display a scrolling terminal menu and return the selected index."""
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
        screen.addnstr(0, 0, prompt, max(1, width - 1), curses.A_BOLD)

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
            return selected_index
        elif key in (ord("q"), 27):
            raise KeyboardInterrupt


def select_option(options: list[str], prompt: str) -> int:
    """Open the terminal menu and return the chosen option's index."""
    if not options:
        raise ValueError("No menu options are available.")

    return curses.wrapper(_selection_screen, options, prompt)


def select_language(languages: list[MenuOption]) -> MenuOption:
    """Ask the user to select one language."""
    if not languages:
        raise ValueError("No language options are available.")

    selected_index = select_option(
        [language.title for language in languages],
        LANGUAGE_PROMPT,
    )
    return languages[selected_index]


def select_book(
    language: MenuOption,
    books: list[MenuOption],
) -> MenuOption | None:
    """Ask the user to select a book, or return to language selection."""
    option_titles = [book.title for book in books]
    option_titles.append(RETURN_TO_LANGUAGES)

    selected_index = select_option(
        option_titles,
        BOOK_PROMPT_TEMPLATE.format(language=language.title),
    )

    if selected_index == len(books):
        return None
    return books[selected_index]


def tts_option_titles(language: MenuOption) -> list[str]:
    """Return human-readable TTS choices for the selected language."""
    return [
        f"Only {language.title}",
        f"Both {language.title} and my language",
    ]


def select_tts_mode(language: MenuOption) -> TTSAudioMode:
    """Ask whether TTS should be used on one or both card sides."""
    modes = [
        TTSAudioMode.SELECTED_LANGUAGE_ONLY,
        TTSAudioMode.BOTH_LANGUAGES,
    ]
    selected_index = select_option(tts_option_titles(language), TTS_PROMPT)
    return modes[selected_index]


def tts_mode_title(language: MenuOption, mode: TTSAudioMode) -> str:
    """Describe a saved TTS choice using the selected language's name."""
    option_index = 0 if mode is TTSAudioMode.SELECTED_LANGUAGE_ONLY else 1
    return tts_option_titles(language)[option_index]


def prompt_output_directory(default_directory: Path) -> Path:
    """Ask where to save the deck, using the project output by default."""
    entered_path = input(
        f"Type output directory (default is {default_directory}): "
    ).strip()
    if not entered_path:
        return default_directory.resolve()
    return Path(entered_path).expanduser().resolve()


def main() -> None:
    """Prompt for deck choices, scrape the book, and create its package."""
    progress = TerminalProgress()
    try:
        languages = get_language_options()

        while True:
            selected_language = select_language(languages)
            books = get_book_options(selected_language.menu_id)
            selected_book = select_book(selected_language, books)

            if selected_book is None:
                continue

            selected_tts_mode = select_tts_mode(selected_language)
            project_root = Path(__file__).resolve().parent.parent
            output_directory = prompt_output_directory(project_root / "output")

            progress.update(f"Starting scrape for {selected_book.title}...")
            deck = get_flashcards_for_book(
                selected_book.menu_id,
                selected_book.title,
                progress_callback=progress.update,
            )
            output_path = output_directory / package_filename(deck.title)
            package_path = create_anki_package(
                deck,
                output_path,
                tts_mode=selected_tts_mode,
                progress_callback=progress.update,
            )
            break
    except urllib.error.URLError as error:
        raise SystemExit(
            f"Unable to download Language Lab data: {error.reason}"
        ) from error
    except ValueError as error:
        raise SystemExit(str(error)) from error
    except KeyboardInterrupt:
        print("\nSelection cancelled.")
        return
    finally:
        progress.finish()

    print(f"\nSelected language: {selected_language.title}")
    print(f"Selected book: {selected_book.title}")
    print(f"TTS: {tts_mode_title(selected_language, selected_tts_mode)}")
    print(f"Created {deck.card_count} Anki cards:")
    print(package_path)


if __name__ == "__main__":
    main()
