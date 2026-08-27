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
PMP_BASIC_GERMAN_CHAPTER_TITLE = (
    "2. Vowel combinations and consonant combinations"
)
PMP_BASIC_GERMAN_SECTION_TITLE = "Wortschatz (p.9)"


class TestPmpBasicGermanFlashcards:
    def test_maps_real_card_data_and_source_hierarchy(self, monkeypatch):
        payload = [
            {
                "Card_ID": 354760,
                "SideA": "ich",
                "SideB": "I",
                "SideAAudio": None,
                "SideBAudio": None,
                "SideALabel": "de-DE",
                "SideBLabel": "en-US",
                "TTSAudio": True,
                "TTSSideA": None,
                "TTSSideB": None,
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
            PMP_BASIC_GERMAN_CHAPTER_TITLE,
            PMP_BASIC_GERMAN_SECTION_TITLE,
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
                    chapter_title=PMP_BASIC_GERMAN_CHAPTER_TITLE,
                    section_title=PMP_BASIC_GERMAN_SECTION_TITLE,
                    source="Flashcards",
                    tts_audio=True,
                    side_a_language="de-DE",
                    side_b_language="en-US",
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
                    chapter_title=PMP_BASIC_GERMAN_CHAPTER_TITLE,
                    section_title=PMP_BASIC_GERMAN_SECTION_TITLE,
                    source="Flashcards",
                )
            ),
        ]
        assert captured_call == {
            "url": scraper.FLASHCARD_URL_TEMPLATE.format(
                menu_id=PMP_BASIC_GERMAN_STUDY_DECK_ID
            ),
            "timeout": scraper.DEFAULT_TIMEOUT_SECONDS,
        }

    def test_maps_real_audio_card_and_recording_url(self, monkeypatch):
        payload = [
            {
                "Card_ID": 354838,
                "SideAAudio": None,
                "ExampleAudio": "1260120902/BGE%2004-02-01.mp3",
                "SideA": "Das ist ___ Vater.",
                "SideB": "Das ist der Vater.",
                "TTSAudio": False,
            },
            {
                "Card_ID": 368254,
                "SideAAudio": None,
                "ExampleAudio": "1260120902/BGE%2037-02-04.mp3",
                "SideA": None,
                "SideB": "Kommst du ohne ihn?",
            },
            {
                "Card_ID": 999999,
                "SideAAudio": None,
                "ExampleAudio": None,
                "SideA": "Guten Tag",
                "SideB": "Good afternoon",
                "TTSAudio": True,
                "SideALabel": "de-DE",
                "SideBLabel": "en-US",
                "TTSSideA": None,
                "TTSSideB": None,
            },
        ]
        captured_call = {}

        def fake_get_json(url, timeout):
            captured_call["url"] = url
            captured_call["timeout"] = timeout
            return payload

        monkeypatch.setattr(scraper, "get_json", fake_get_json)

        with pytest.warns(RuntimeWarning, match="Audio card 368254"):
            result = scraper.get_audio_deck(
                menu_id=74976,
                chapter_id=33428,
                section_id=74976,
                chapter_title="4. Nouns",
                section_title="Übung 4.2",
            )

        assert result == [
            Flashcard(
                Card(
                    card_id=354838,
                    side_a="Das ist ___ Vater.",
                    side_b="Das ist der Vater.",
                    side_a_audio=None,
                    side_b_audio=(
                        "https://mhelanguagelab.s3.amazonaws.com/"
                        "1260120902/BGE%2004-02-01.mp3"
                    ),
                    chapter_id=33428,
                    section_id=74976,
                    chapter_title="4. Nouns",
                    section_title="Übung 4.2",
                    source="Audio",
                    tts_audio=False,
                )
            ),
            Flashcard(
                Card(
                    card_id=999999,
                    side_a="Guten Tag",
                    side_b="Good afternoon",
                    side_a_audio=None,
                    side_b_audio=None,
                    chapter_id=33428,
                    section_id=74976,
                    chapter_title="4. Nouns",
                    section_title="Übung 4.2",
                    source="Audio",
                    tts_audio=True,
                    side_a_language="de-DE",
                    side_b_language="en-US",
                )
            ),
        ]
        assert captured_call == {
            "url": scraper.AUDIO_CARD_URL_TEMPLATE.format(menu_id=74976),
            "timeout": scraper.DEFAULT_TIMEOUT_SECONDS,
        }

    def test_merges_matching_flashcard_and_audio_hierarchy(self, monkeypatch):
        audio_menu_id = 31056
        audio_chapter_id = 33426
        matched_audio_deck_id = 74976
        unmatched_audio_deck_id = 74979
        unmatched_audio_section_title = "Übung 2.2"
        menu_graph = {
            PMP_BASIC_GERMAN_BOOK_ID: [
                MenuOption(
                    PMP_BASIC_GERMAN_FLASHCARDS_MENU_ID,
                    "Flashcards",
                    "N/A",
                ),
                MenuOption(audio_menu_id, "Audio", "N/A"),
            ],
            PMP_BASIC_GERMAN_FLASHCARDS_MENU_ID: [
                MenuOption(
                    PMP_BASIC_GERMAN_CHAPTER_ID,
                    PMP_BASIC_GERMAN_CHAPTER_TITLE,
                    "N/A",
                )
            ],
            PMP_BASIC_GERMAN_CHAPTER_ID: [
                MenuOption(
                    PMP_BASIC_GERMAN_SECTION_ID,
                    PMP_BASIC_GERMAN_SECTION_TITLE,
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
            audio_menu_id: [
                MenuOption(
                    audio_chapter_id,
                    f"  {PMP_BASIC_GERMAN_CHAPTER_TITLE}  ",
                    "N/A",
                )
            ],
            audio_chapter_id: [
                MenuOption(
                    matched_audio_deck_id,
                    "<i>Wortschatz</i> (p.9)",
                    "Record Yourself",
                ),
                MenuOption(
                    unmatched_audio_deck_id,
                    unmatched_audio_section_title,
                    "Record Yourself",
                ),
            ],
        }
        expected_flashcard = Flashcard(
            Card(
                card_id=354760,
                side_a="ich",
                side_b="I",
                side_a_audio=None,
                side_b_audio=None,
                chapter_id=PMP_BASIC_GERMAN_CHAPTER_ID,
                section_id=PMP_BASIC_GERMAN_SECTION_ID,
                chapter_title=PMP_BASIC_GERMAN_CHAPTER_TITLE,
                section_title=PMP_BASIC_GERMAN_SECTION_TITLE,
                source="Flashcards",
            )
        )
        requested_flashcard_decks = []
        requested_audio_decks = []

        monkeypatch.setattr(
            scraper,
            "get_menu_options",
            lambda parent_id, timeout: menu_graph[parent_id],
        )

        def fake_get_flashcard_deck(
            menu_id,
            chapter_id,
            section_id,
            chapter_title,
            section_title,
            timeout,
        ):
            requested_flashcard_decks.append(
                (
                    menu_id,
                    chapter_id,
                    section_id,
                    chapter_title,
                    section_title,
                )
            )
            return [expected_flashcard]

        def fake_get_audio_deck(
            menu_id,
            chapter_id,
            section_id,
            chapter_title,
            section_title,
            timeout,
        ):
            requested_audio_decks.append(
                (
                    menu_id,
                    chapter_id,
                    section_id,
                    chapter_title,
                    section_title,
                )
            )
            return [
                Flashcard(
                    Card(
                        card_id=menu_id,
                        side_a=f"Audio prompt {menu_id}",
                        side_b=f"Audio answer {menu_id}",
                        side_a_audio=None,
                        side_b_audio=f"https://example.com/{menu_id}.mp3",
                        chapter_id=chapter_id,
                        section_id=section_id,
                        chapter_title=chapter_title,
                        section_title=section_title,
                        source="Audio",
                    )
                )
            ]

        monkeypatch.setattr(
            scraper,
            "get_flashcard_deck",
            fake_get_flashcard_deck,
        )
        monkeypatch.setattr(
            scraper,
            "get_audio_deck",
            fake_get_audio_deck,
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
                    title=PMP_BASIC_GERMAN_CHAPTER_TITLE,
                    sections=[
                        Section(
                            section_id=PMP_BASIC_GERMAN_SECTION_ID,
                            title=PMP_BASIC_GERMAN_SECTION_TITLE,
                            flashcards=[
                                expected_flashcard,
                                Flashcard(
                                    Card(
                                        card_id=matched_audio_deck_id,
                                        side_a=(
                                            f"Audio prompt {matched_audio_deck_id}"
                                        ),
                                        side_b=(
                                            f"Audio answer {matched_audio_deck_id}"
                                        ),
                                        side_a_audio=None,
                                        side_b_audio=(
                                            "https://example.com/"
                                            f"{matched_audio_deck_id}.mp3"
                                        ),
                                        chapter_id=PMP_BASIC_GERMAN_CHAPTER_ID,
                                        section_id=PMP_BASIC_GERMAN_SECTION_ID,
                                        chapter_title=(
                                            PMP_BASIC_GERMAN_CHAPTER_TITLE
                                        ),
                                        section_title=(
                                            PMP_BASIC_GERMAN_SECTION_TITLE
                                        ),
                                        source="Audio",
                                    )
                                ),
                            ],
                        ),
                        Section(
                            section_id=unmatched_audio_deck_id,
                            title=unmatched_audio_section_title,
                            flashcards=[
                                Flashcard(
                                    Card(
                                        card_id=unmatched_audio_deck_id,
                                        side_a=(
                                            f"Audio prompt {unmatched_audio_deck_id}"
                                        ),
                                        side_b=(
                                            f"Audio answer {unmatched_audio_deck_id}"
                                        ),
                                        side_a_audio=None,
                                        side_b_audio=(
                                            "https://example.com/"
                                            f"{unmatched_audio_deck_id}.mp3"
                                        ),
                                        chapter_id=PMP_BASIC_GERMAN_CHAPTER_ID,
                                        section_id=unmatched_audio_deck_id,
                                        chapter_title=(
                                            PMP_BASIC_GERMAN_CHAPTER_TITLE
                                        ),
                                        section_title=(
                                            unmatched_audio_section_title
                                        ),
                                        source="Audio",
                                    )
                                )
                            ],
                        ),
                    ],
                )
            ],
        )
        assert requested_flashcard_decks == [
            (
                PMP_BASIC_GERMAN_STUDY_DECK_ID,
                PMP_BASIC_GERMAN_CHAPTER_ID,
                PMP_BASIC_GERMAN_SECTION_ID,
                PMP_BASIC_GERMAN_CHAPTER_TITLE,
                PMP_BASIC_GERMAN_SECTION_TITLE,
            )
        ]
        assert requested_audio_decks == [
            (
                matched_audio_deck_id,
                PMP_BASIC_GERMAN_CHAPTER_ID,
                PMP_BASIC_GERMAN_SECTION_ID,
                PMP_BASIC_GERMAN_CHAPTER_TITLE,
                PMP_BASIC_GERMAN_SECTION_TITLE,
            ),
            (
                unmatched_audio_deck_id,
                PMP_BASIC_GERMAN_CHAPTER_ID,
                unmatched_audio_deck_id,
                PMP_BASIC_GERMAN_CHAPTER_TITLE,
                unmatched_audio_section_title,
            ),
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
                "Chapter 1",
                "Wortschatz (p.9)",
                "Flashcards",
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
            pytest.param(
                [
                    {
                        "Card_ID": 1,
                        "SideA": "ich",
                        "SideB": "I",
                        "TTSAudio": "yes",
                    }
                ],
                "TTSAudio",
                id="card-has-invalid-tts-flag",
            ),
            pytest.param(
                [
                    {
                        "Card_ID": 1,
                        "SideA": "ich",
                        "SideB": "I",
                        "TTSAudio": True,
                        "SideALabel": 123,
                    }
                ],
                "SideALabel",
                id="card-has-invalid-tts-language",
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
            scraper.get_flashcard_deck(
                23947,
                1550,
                11267,
                PMP_BASIC_GERMAN_CHAPTER_TITLE,
                PMP_BASIC_GERMAN_SECTION_TITLE,
            )

    def test_reports_when_a_book_has_no_card_content_menu(self, monkeypatch):
        monkeypatch.setattr(
            scraper,
            "get_menu_options",
            lambda parent_id, timeout: [MenuOption(84275, "Details", "N/A")],
        )

        with pytest.raises(ValueError, match="Flashcards or Audio menu"):
            scraper.get_flashcards_for_book(85, "PMP Basic German")
