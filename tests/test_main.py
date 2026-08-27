import curses

import pytest

import main as application


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


class TestTerminalLanguageSelection:
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

        selected = application._selection_screen(
            screen,
            ["English", "French", "German", "Italian", "Spanish"],
        )

        assert selected == "Italian"
        assert "> Italian" in screen.rendered_text
        assert screen.keypad_enabled is True

    def test_rejects_an_empty_language_list(self):
        with pytest.raises(ValueError, match="No language options"):
            application.select_language([])

    def test_main_fetches_options_and_prints_the_selection(
        self,
        monkeypatch,
        capsys,
    ):
        options = ["English (ESL)", "Spanish", "Arabic"]
        received_options = []

        monkeypatch.setattr(
            application,
            "get_language_options",
            lambda: options,
        )

        def fake_select_language(language_options):
            received_options.extend(language_options)
            return "Spanish"

        monkeypatch.setattr(
            application,
            "select_language",
            fake_select_language,
        )

        application.main()

        assert received_options == options
        assert capsys.readouterr().out == "\nSelected language: Spanish\n"
