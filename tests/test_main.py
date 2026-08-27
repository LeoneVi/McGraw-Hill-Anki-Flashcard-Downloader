import curses
from pathlib import Path

import pytest

from flashcard_models import Card, Chapter, Deck, Flashcard, Section
from language_lab_api import MenuOption
import main as application

"""
 To run all tests, use the following command:
 .venv/bin/python -m pytest
"""

def make_deck(title: str, front: str, back: str) -> Deck:
    flashcard = Flashcard(
        Card(
            card_id=1,
            side_a=front,
            side_b=back,
            side_a_audio=None,
            side_b_audio=None,
            chapter_id=10,
            section_id=11,
        )
    )
    return Deck(
        title=title,
        chapters=[
            Chapter(
                chapter_id=10,
                title="Chapter",
                sections=[Section(11, "Section", [flashcard])],
            )
        ],
    )


class FakeScreen:
    def __init__(self, keys, height=5, width=40):
        self.keys = iter(keys)
        self.height = height
        self.width = width
        self.rendered_text = []

    def keypad(self, enabled):
        self.keypad_enabled = enabled

    def getmaxyx(self):
        return self.height, self.width

    def erase(self):
        pass

    def addnstr(self, row, column, text, length, style):
        self.rendered_text.append(text)

    def refresh(self):
        pass

    def getch(self):
        return next(self.keys)


class TestTerminalMenu:
    def test_arrow_keys_move_and_scroll_before_enter(self, monkeypatch):
        screen = FakeScreen(
            [
                curses.KEY_DOWN,
                curses.KEY_DOWN,
                curses.KEY_DOWN,
                10,
            ]
        )
        monkeypatch.setattr(application.curses, "curs_set", lambda visibility: None)

        selected_index = application._selection_screen(
            screen,
            ["English", "French", "German", "Italian", "Spanish"],
            "Choose an option",
        )

        assert selected_index == 3
        assert "> Italian" in screen.rendered_text
        assert screen.keypad_enabled is True

    def test_rejects_an_empty_menu(self):
        with pytest.raises(ValueError, match="No menu options"):
            application.select_option([], "Choose an option")


class TestLanguageAndBookSelection:
    def test_main_fetches_books_for_language_and_prints_selection(
        self,
        monkeypatch,
        capsys,
    ):
        languages = [
            MenuOption(1, "English (ESL)"),
            MenuOption(5, "Spanish"),
        ]
        books = [
            MenuOption(43, "Complete Medical Spanish"),
            MenuOption(50, "Complete Spanish Step-by-Step"),
        ]
        received_language_ids = []
        received_book_ids = []

        monkeypatch.setattr(
            application,
            "get_language_options",
            lambda: languages,
        )

        def fake_get_book_options(language_id):
            received_language_ids.append(language_id)
            return books

        monkeypatch.setattr(
            application,
            "get_book_options",
            fake_get_book_options,
        )
        monkeypatch.setattr(
            application,
            "select_language",
            lambda options: options[1],
        )
        monkeypatch.setattr(
            application,
            "select_book",
            lambda language, options: options[0],
        )

        def fake_get_flashcards_for_book(book_id, book_title):
            received_book_ids.append((book_id, book_title))
            return make_deck(book_title, "hola", "hello")

        monkeypatch.setattr(
            application,
            "get_flashcards_for_book",
            fake_get_flashcards_for_book,
        )
        monkeypatch.setattr(
            application,
            "create_anki_package",
            lambda deck, output_path: Path(
                "/tmp/Complete_Medical_Spanish.apkg"
            ),
        )

        application.main()

        assert received_language_ids == [5]
        assert received_book_ids == [(43, "Complete Medical Spanish")]
        assert capsys.readouterr().out == (
            "\nScraping flashcards for Complete Medical Spanish...\n"
            "\nSelected language: Spanish\n"
            "Selected book: Complete Medical Spanish\n"
            "Created 1 Anki cards:\n"
            "/tmp/Complete_Medical_Spanish.apkg\n"
        )

    def test_return_option_goes_back_to_language_selection(
        self,
        monkeypatch,
        capsys,
    ):
        spanish = MenuOption(5, "Spanish")
        french = MenuOption(2, "French")
        spanish_books = [MenuOption(43, "Complete Medical Spanish")]
        french_books = [MenuOption(20, "French Grammar")]
        language_choices = iter([spanish, french])
        book_choices = iter([None, french_books[0]])
        received_language_ids = []

        monkeypatch.setattr(
            application,
            "get_language_options",
            lambda: [spanish, french],
        )
        monkeypatch.setattr(
            application,
            "select_language",
            lambda options: next(language_choices),
        )

        def fake_get_book_options(language_id):
            received_language_ids.append(language_id)
            if language_id == spanish.menu_id:
                return spanish_books
            return french_books

        monkeypatch.setattr(
            application,
            "get_book_options",
            fake_get_book_options,
        )
        monkeypatch.setattr(
            application,
            "select_book",
            lambda language, books: next(book_choices),
        )
        monkeypatch.setattr(
            application,
            "get_flashcards_for_book",
            lambda book_id, book_title: make_deck(
                book_title,
                "bonjour",
                "hello",
            ),
        )
        monkeypatch.setattr(
            application,
            "create_anki_package",
            lambda deck, output_path: Path("/tmp/French_Grammar.apkg"),
        )

        application.main()

        assert received_language_ids == [5, 2]
        assert "Selected language: French" in capsys.readouterr().out

    def test_book_menu_adds_return_to_languages(self, monkeypatch):
        language = MenuOption(5, "Spanish")
        books = [MenuOption(43, "Complete Medical Spanish")]
        received_menu = {}

        def fake_select_option(options, prompt):
            received_menu["options"] = options
            received_menu["prompt"] = prompt
            return 1

        monkeypatch.setattr(application, "select_option", fake_select_option)

        result = application.select_book(language, books)

        assert result is None
        assert received_menu["options"] == [
            "Complete Medical Spanish",
            application.RETURN_TO_LANGUAGES,
        ]
        assert "Spanish" in received_menu["prompt"]
