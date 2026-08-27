import json

import pytest

from flashcard_models import Card, Chapter, Deck, Flashcard, Section
from language_lab_api import MenuOption
import scrape_flashcards as scraper


PMP_BASIC_GERMAN_BOOK_ID = 85
PMP_BASIC_GERMAN_FLASHCARDS_MENU_ID = 30912
PMP_BASIC_GERMAN_CHAPTER_ID = 1550
PMP_BASIC_GERMAN_SECTION_ID = 11267
PMP_BASIC_GERMAN_STUDY_DECK_ID = 23947


class TestPmpBasicGermanFlashcards:
    def test_maps_real_card_data_and_source_hierarchy(self, monkeypatch):
        payload = [
            {
                "Card_ID": 354760,
                "SideA": "ich",
                "SideB": "I",
                "SideAAudio": None,
                "SideBAudio": None,
            },
            {
                "Card_ID": 354761,
                "SideA": "du",
                "SideB": "you (singular, familiar)",
                "SideAAudio": "https://example.com/du.mp3",
                "SideBAudio": None,
            },
        ]
        captured_call = {}

        def fake_get_json(url, timeout):
            captured_call["url"] = url
            captured_call["timeout"] = timeout
            return payload

        monkeypatch.setattr(scraper, "get_json", fake_get_json)

        result = scraper.get_flashcard_deck(
            PMP_BASIC_GERMAN_STUDY_DECK_ID,
            PMP_BASIC_GERMAN_CHAPTER_ID,
            PMP_BASIC_GERMAN_SECTION_ID,
        )

        assert result == [
            Flashcard(
                Card(
                    card_id=354760,
                    side_a="ich",
                    side_b="I",
                    side_a_audio=None,
                    side_b_audio=None,
                    chapter_id=PMP_BASIC_GERMAN_CHAPTER_ID,
                    section_id=PMP_BASIC_GERMAN_SECTION_ID,
                )
            ),
            Flashcard(
                Card(
                    card_id=354761,
                    side_a="du",
                    side_b="you (singular, familiar)",
                    side_a_audio="https://example.com/du.mp3",
                    side_b_audio=None,
                    chapter_id=PMP_BASIC_GERMAN_CHAPTER_ID,
                    section_id=PMP_BASIC_GERMAN_SECTION_ID,
                )
            ),
        ]
        assert captured_call == {
            "url": scraper.FLASHCARD_URL_TEMPLATE.format(
                menu_id=PMP_BASIC_GERMAN_STUDY_DECK_ID
            ),
            "timeout": scraper.DEFAULT_TIMEOUT_SECONDS,
        }

    def test_builds_the_pmp_basic_german_tree(self, monkeypatch):
        menu_graph = {
            PMP_BASIC_GERMAN_BOOK_ID: [
                MenuOption(
                    PMP_BASIC_GERMAN_FLASHCARDS_MENU_ID,
                    "Flashcards",
                    "N/A",
                ),
                MenuOption(31056, "Audio", "N/A"),
            ],
            PMP_BASIC_GERMAN_FLASHCARDS_MENU_ID: [
                MenuOption(
                    PMP_BASIC_GERMAN_CHAPTER_ID,
                    "2. Vowel combinations and consonant combinations",
                    "N/A",
                )
            ],
            PMP_BASIC_GERMAN_CHAPTER_ID: [
                MenuOption(
                    PMP_BASIC_GERMAN_SECTION_ID,
                    "Wortschatz (p.9)",
                    "N/A",
                )
            ],
            PMP_BASIC_GERMAN_SECTION_ID: [
                MenuOption(
                    PMP_BASIC_GERMAN_STUDY_DECK_ID,
                    "Flashcards: Study Mode",
                    "Flashcards: Study Mode",
                ),
                MenuOption(
                    30233,
                    "Flashcards: Quiz Mode",
                    "Flashcards: Quiz Mode",
                ),
            ],
        }
        expected_flashcard = Flashcard(
            Card(
                354760,
                "ich",
                "I",
                None,
                None,
                PMP_BASIC_GERMAN_CHAPTER_ID,
                PMP_BASIC_GERMAN_SECTION_ID,
            )
        )
        requested_decks = []

        monkeypatch.setattr(
            scraper,
            "get_menu_options",
            lambda parent_id, timeout: menu_graph[parent_id],
        )

        def fake_get_flashcard_deck(
            menu_id,
            chapter_id,
            section_id,
            timeout,
        ):
            requested_decks.append((menu_id, chapter_id, section_id))
            return [expected_flashcard]

        monkeypatch.setattr(
            scraper,
            "get_flashcard_deck",
            fake_get_flashcard_deck,
        )

        result = scraper.get_flashcards_for_book(
            PMP_BASIC_GERMAN_BOOK_ID,
            "PMP Basic German",
        )

        assert result == Deck(
            title="PMP Basic German",
            chapters=[
                Chapter(
                    chapter_id=PMP_BASIC_GERMAN_CHAPTER_ID,
                    title="2. Vowel combinations and consonant combinations",
                    sections=[
                        Section(
                            section_id=PMP_BASIC_GERMAN_SECTION_ID,
                            title="Wortschatz (p.9)",
                            flashcards=[expected_flashcard],
                        )
                    ],
                )
            ],
        )
        assert requested_decks == [
            (
                PMP_BASIC_GERMAN_STUDY_DECK_ID,
                PMP_BASIC_GERMAN_CHAPTER_ID,
                PMP_BASIC_GERMAN_SECTION_ID,
            )
        ]

    def test_formats_unicode_and_source_metadata_as_json(self):
        flashcard = Flashcard(
            Card(
                1,
                "das Mädchen",
                "the girl",
                None,
                None,
                10,
                11,
            )
        )

        result = scraper.flashcards_to_json([flashcard])

        assert json.loads(result) == [flashcard.anki_fields()]
        assert "Mädchen" in result

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            pytest.param(
                {"Card_ID": 1, "SideA": "ich", "SideB": "I"},
                "return a list",
                id="payload-is-not-a-list",
            ),
            pytest.param(
                [{"SideA": "ich", "SideB": "I"}],
                "Card_ID",
                id="card-has-no-id",
            ),
            pytest.param(
                [{"Card_ID": 1, "SideB": "I"}],
                "SideA",
                id="card-has-no-front",
            ),
            pytest.param(
                [{"Card_ID": 1, "SideA": "ich"}],
                "SideB",
                id="card-has-no-back",
            ),
            pytest.param(
                [
                    {
                        "Card_ID": 1,
                        "SideA": "ich",
                        "SideB": "I",
                        "SideAAudio": 123,
                    }
                ],
                "SideAAudio",
                id="card-has-invalid-audio",
            ),
        ],
    )
    def test_rejects_invalid_card_data(
        self,
        monkeypatch,
        payload,
        message,
    ):
        monkeypatch.setattr(
            scraper,
            "get_json",
            lambda url, timeout: payload,
        )

        with pytest.raises(ValueError, match=message):
            scraper.get_flashcard_deck(23947, 1550, 11267)

    def test_reports_when_a_book_has_no_flashcards_menu(self, monkeypatch):
        monkeypatch.setattr(
            scraper,
            "get_menu_options",
            lambda parent_id, timeout: [MenuOption(31056, "Audio", "N/A")],
        )

        with pytest.raises(ValueError, match="does not have a Flashcards menu"):
            scraper.get_flashcards_for_book(85, "PMP Basic German")
