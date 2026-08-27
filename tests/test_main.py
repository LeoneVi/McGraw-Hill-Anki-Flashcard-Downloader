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
            chapter_title="Chapter",
            section_title="Section",
            source="Flashcards",
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

    def test_progress_replaces_one_terminal_line(self, capsys):
        progress = application.TerminalProgress()

        progress.update("Scraping chapter 1")
        progress.update("Done")
        progress.finish()

        assert capsys.readouterr().out == (
            "\rScraping chapter 1\rDone              \n"
        )


class TestLanguageAndBookSelection:
    def test_main_fetches_books_for_language_and_prints_selection(
        self,
        monkeypatch,
        capsys,
        tmp_path,
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
        received_output_paths = []
        received_tts_languages = []
        received_tts_modes = []
        progress_messages = []

        class FakeProgress:
            def update(self, message):
                progress_messages.append(message)

            def finish(self):
                pass

        monkeypatch.setattr(application, "TerminalProgress", FakeProgress)

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

        def fake_select_tts_mode(language):
            received_tts_languages.append(language)
            return application.TTSAudioMode.SELECTED_LANGUAGE_ONLY

        monkeypatch.setattr(
            application,
            "select_tts_mode",
            fake_select_tts_mode,
        )
        selected_output_directory = tmp_path / "my decks"
        monkeypatch.setattr(
            application,
            "prompt_output_directory",
            lambda default_directory: selected_output_directory,
        )

        def fake_get_flashcards_for_book(
            book_id,
            book_title,
            progress_callback,
        ):
            received_book_ids.append((book_id, book_title))
            progress_callback("Scraped cards")
            return make_deck(book_title, "hola", "hello")

        monkeypatch.setattr(
            application,
            "get_flashcards_for_book",
            fake_get_flashcards_for_book,
        )

        def fake_create_anki_package(
            deck,
            output_path,
            tts_mode,
            progress_callback,
        ):
            received_output_paths.append(output_path)
            received_tts_modes.append(tts_mode)
            progress_callback("Created package")
            return output_path

        monkeypatch.setattr(
            application,
            "create_anki_package",
            fake_create_anki_package,
        )

        application.main()

        assert received_language_ids == [5]
        assert received_book_ids == [(43, "Complete Medical Spanish")]
        assert received_tts_languages == [languages[1]]
        assert received_tts_modes == [
            application.TTSAudioMode.SELECTED_LANGUAGE_ONLY
        ]
        assert received_output_paths == [
            selected_output_directory
            / "Complete_Medical_Spanish.apkg"
        ]
        assert progress_messages == [
            "Starting scrape for Complete Medical Spanish...",
            "Scraped cards",
            "Created package",
        ]
        assert capsys.readouterr().out == (
            "\nSelected language: Spanish\n"
            "Selected book: Complete Medical Spanish\n"
            "TTS: Only Spanish\n"
            "Created 1 Anki cards:\n"
            f"{selected_output_directory / 'Complete_Medical_Spanish.apkg'}\n"
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
            "select_tts_mode",
            lambda language: application.TTSAudioMode.BOTH_LANGUAGES,
        )
        monkeypatch.setattr(
            application,
            "prompt_output_directory",
            lambda default_directory: Path("/tmp"),
        )
        monkeypatch.setattr(
            application,
            "get_flashcards_for_book",
            lambda book_id, book_title, progress_callback: make_deck(
                book_title,
                "bonjour",
                "hello",
            ),
        )
        monkeypatch.setattr(
            application,
            "create_anki_package",
            lambda deck, output_path, **kwargs: Path(
                "/tmp/French_Grammar.apkg"
            ),
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

    def test_tts_menu_uses_the_remembered_language(self, monkeypatch):
        language = MenuOption(4, "German")
        received_menu = {}

        def fake_select_option(options, prompt):
            received_menu["options"] = options
            received_menu["prompt"] = prompt
            return 1

        monkeypatch.setattr(application, "select_option", fake_select_option)

        result = application.select_tts_mode(language)

        assert result is application.TTSAudioMode.BOTH_LANGUAGES
        assert received_menu == {
            "options": ["Only German", "Both German and my language"],
            "prompt": application.TTS_PROMPT,
        }

    def test_blank_output_uses_the_project_output_directory(
        self,
        monkeypatch,
        tmp_path,
    ):
        default_directory = tmp_path / "output"
        captured_prompt = []

        def fake_input(prompt):
            captured_prompt.append(prompt)
            return ""

        monkeypatch.setattr("builtins.input", fake_input)

        result = application.prompt_output_directory(default_directory)

        assert result == default_directory.resolve()
        assert str(default_directory) in captured_prompt[0]

    def test_typed_output_directory_overrides_the_default(
        self,
        monkeypatch,
        tmp_path,
    ):
        selected_directory = tmp_path / "custom decks"
        monkeypatch.setattr(
            "builtins.input",
            lambda prompt: str(selected_directory),
        )

        result = application.prompt_output_directory(tmp_path / "output")

        assert result == selected_directory.resolve()
