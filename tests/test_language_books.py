import pytest

from language_lab_api import MenuOption
import scrape_language_books as scraper


class TestLanguageBooks:
    def test_returns_books_for_the_selected_language(self, monkeypatch):
        expected_books = [
            MenuOption(43, "Complete Medical Spanish"),
            MenuOption(50, "Complete Spanish Step-by-Step"),
        ]
        captured_call = {}

        def fake_get_menu_options(parent_id, timeout):
            captured_call["parent_id"] = parent_id
            captured_call["timeout"] = timeout
            return expected_books

        monkeypatch.setattr(
            scraper,
            "get_menu_options",
            fake_get_menu_options,
        )

        result = scraper.get_book_options(language_id=5)

        assert result == expected_books
        assert captured_call == {
            "parent_id": 5,
            "timeout": scraper.DEFAULT_TIMEOUT_SECONDS,
        }

    @pytest.mark.parametrize("language_id", [0, -1, "5", True, None])
    def test_rejects_an_invalid_language_id(self, language_id):
        with pytest.raises(ValueError, match="positive menu ID"):
            scraper.get_book_options(language_id)
