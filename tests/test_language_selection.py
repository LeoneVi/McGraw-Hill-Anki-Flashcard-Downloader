from language_lab_api import MenuOption
import scrape_language_selection as scraper


class TestLanguageSelection:
    def test_expands_other_into_its_language_submenu(self, monkeypatch):
        root_options = [
            MenuOption(1, "English (ESL)"),
            MenuOption(2, "French"),
            MenuOption(3, "German"),
            MenuOption(4, "Italian"),
            MenuOption(5, "Spanish"),
            MenuOption(6, "Other"),
        ]
        other_options = [
            MenuOption(83487, "Arabic"),
            MenuOption(83491, "Chinese"),
            MenuOption(83489, "Japanese"),
            MenuOption(83490, "Korean"),
            MenuOption(86381, "Portuguese"),
            MenuOption(136797, "Russian"),
        ]
        captured_calls = []

        def fake_get_menu_options(parent_id, timeout):
            captured_calls.append((parent_id, timeout))
            if parent_id == scraper.ROOT_MENU_ID:
                return root_options
            return other_options

        monkeypatch.setattr(
            scraper,
            "get_menu_options",
            fake_get_menu_options,
        )

        result = scraper.get_language_options()

        assert result == root_options[:-1] + other_options
        assert all(option.title != "Other" for option in result)
        assert captured_calls == [
            (scraper.ROOT_MENU_ID, scraper.DEFAULT_TIMEOUT_SECONDS),
            (6, scraper.DEFAULT_TIMEOUT_SECONDS),
        ]

    def test_passes_a_custom_timeout_to_both_menus(self, monkeypatch):
        captured_calls = []

        def fake_get_menu_options(parent_id, timeout):
            captured_calls.append((parent_id, timeout))
            if parent_id == scraper.ROOT_MENU_ID:
                return [MenuOption(6, "Other")]
            return [MenuOption(83487, "Arabic")]

        monkeypatch.setattr(
            scraper,
            "get_menu_options",
            fake_get_menu_options,
        )

        scraper.get_language_options(timeout=25)

        assert captured_calls == [(0, 25), (6, 25)]
