"""Scrape a selected Language Lab book into a structured deck."""

from collections.abc import Iterable
import html
import json
import re
from urllib.parse import urljoin
import warnings

from flashcard_models import (
    AUDIO_SOURCE,
    FLASHCARDS_SOURCE,
    Card,
    Chapter,
    Deck,
    Flashcard,
    Section,
)
from language_lab_api import (
    DEFAULT_TIMEOUT_SECONDS,
    get_json,
    get_menu_options,
)


FLASHCARD_URL_TEMPLATE = (
    "https://mhe-language-lab.azurewebsites.net/api/GetFlashCards?menuID={menu_id}"
)
AUDIO_CARD_URL_TEMPLATE = (
    "https://mhe-language-lab.azurewebsites.net/api/"
    "GetRecordYourselfCards?menuID={menu_id}"
)
AUDIO_MEDIA_BASE_URL = "https://mhelanguagelab.s3.amazonaws.com/"
FLASHCARDS_MENU_TITLE = "Flashcards"
AUDIO_MENU_TITLE = "Audio"
STUDY_MODE_DECK_TYPE = "Flashcards: Study Mode"
RECORD_YOURSELF_DECK_TYPE = "Record Yourself"


def _optional_text(record: dict, field_name: str) -> str | None:
    value = record.get(field_name)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"A flashcard has invalid {field_name} data.")
    return value


def _tts_enabled(record: dict) -> bool:
    value = record.get("TTSAudio", False)
    if not isinstance(value, bool):
        raise ValueError("A flashcard has invalid TTSAudio data.")
    return value


def _audio_url(record: dict, field_name: str) -> str | None:
    value = _optional_text(record, field_name)
    if not value:
        return None
    return urljoin(AUDIO_MEDIA_BASE_URL, value)


def _matching_key(title: str) -> str:
    without_html = re.sub(r"<[^>]+>", "", html.unescape(title))
    return " ".join(without_html.split()).casefold()


def _get_card_deck(
    url: str,
    chapter_id: int,
    section_id: int,
    chapter_title: str,
    section_title: str,
    source: str,
    side_b_audio_field: str,
    timeout: int,
) -> list[Flashcard]:
    payload = get_json(url, timeout)

    if not isinstance(payload, list):
        raise ValueError("Expected the card API to return a list.")

    cards = []
    for card_data in payload:
        if (
            not isinstance(card_data, dict)
            or not isinstance(card_data.get("Card_ID"), int)
            or isinstance(card_data.get("Card_ID"), bool)
        ):
            raise ValueError("A flashcard is missing a valid Card_ID.")
        if not isinstance(card_data.get("SideA"), str) or not isinstance(
            card_data.get("SideB"), str
        ):
            if source == AUDIO_SOURCE:
                warnings.warn(
                    f"Skipping malformed Audio card {card_data['Card_ID']} "
                    "because SideA or SideB text is missing.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            if not isinstance(card_data.get("SideA"), str):
                raise ValueError("A flashcard is missing valid SideA text.")
            raise ValueError("A flashcard is missing valid SideB text.")

        card = Card(
            card_id=card_data["Card_ID"],
            side_a=card_data["SideA"],
            side_b=card_data["SideB"],
            side_a_audio=_audio_url(card_data, "SideAAudio"),
            side_b_audio=_audio_url(card_data, side_b_audio_field),
            chapter_id=chapter_id,
            section_id=section_id,
            chapter_title=chapter_title,
            section_title=section_title,
            source=source,
            tts_audio=_tts_enabled(card_data),
            side_a_language=_optional_text(card_data, "SideALabel"),
            side_b_language=_optional_text(card_data, "SideBLabel"),
            tts_side_a=_optional_text(card_data, "TTSSideA"),
            tts_side_b=_optional_text(card_data, "TTSSideB"),
        )
        cards.append(Flashcard(card=card))

    return cards


def get_flashcard_deck(
    menu_id: int,
    chapter_id: int,
    section_id: int,
    chapter_title: str,
    section_title: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[Flashcard]:
    """Download one study-mode deck and retain its source hierarchy."""
    if not isinstance(menu_id, int) or isinstance(menu_id, bool) or menu_id <= 0:
        raise ValueError("A flashcard deck must have a positive menu ID.")

    return _get_card_deck(
        url=FLASHCARD_URL_TEMPLATE.format(menu_id=menu_id),
        chapter_id=chapter_id,
        section_id=section_id,
        chapter_title=chapter_title,
        section_title=section_title,
        source=FLASHCARDS_SOURCE,
        side_b_audio_field="SideBAudio",
        timeout=timeout,
    )


def get_audio_deck(
    menu_id: int,
    chapter_id: int,
    section_id: int,
    chapter_title: str,
    section_title: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[Flashcard]:
    """Download one Audio/Record Yourself deck with real recordings."""
    if not isinstance(menu_id, int) or isinstance(menu_id, bool) or menu_id <= 0:
        raise ValueError("An audio deck must have a positive menu ID.")

    return _get_card_deck(
        url=AUDIO_CARD_URL_TEMPLATE.format(menu_id=menu_id),
        chapter_id=chapter_id,
        section_id=section_id,
        chapter_title=chapter_title,
        section_title=section_title,
        source=AUDIO_SOURCE,
        side_b_audio_field="ExampleAudio",
        timeout=timeout,
    )


def _find_deck_ids(
    parent_id: int,
    wanted_deck_type: str,
    timeout: int,
    visited_menu_ids: set[int],
) -> list[int]:
    """Recursively find one kind of card deck below a section menu."""
    if parent_id in visited_menu_ids:
        return []
    visited_menu_ids.add(parent_id)

    study_deck_ids = []
    for option in get_menu_options(parent_id, timeout):
        if option.deck_type == wanted_deck_type:
            study_deck_ids.append(option.menu_id)
            continue

        if option.deck_type in (None, "N/A"):
            study_deck_ids.extend(
                _find_deck_ids(
                    option.menu_id,
                    wanted_deck_type,
                    timeout,
                    visited_menu_ids,
                )
            )

    return study_deck_ids


def _merge_source_menu(
    source_menu,
    wanted_deck_type: str,
    deck_loader,
    timeout: int,
    chapters: list[Chapter],
    hierarchy_by_title: dict[str, tuple[Chapter, dict[str, Section]]],
) -> None:
    """Merge one content source into the shared chapter/section tree."""
    for chapter_option in get_menu_options(source_menu.menu_id, timeout):
        chapter_key = _matching_key(chapter_option.title)
        hierarchy = hierarchy_by_title.get(chapter_key)

        for section_option in get_menu_options(chapter_option.menu_id, timeout):
            if section_option.deck_type == wanted_deck_type:
                source_deck_ids = [section_option.menu_id]
            elif section_option.deck_type in (None, "N/A"):
                source_deck_ids = _find_deck_ids(
                    section_option.menu_id,
                    wanted_deck_type,
                    timeout,
                    set(),
                )
            else:
                source_deck_ids = []

            if not source_deck_ids:
                continue

            if hierarchy is None:
                chapter = Chapter(
                    chapter_id=chapter_option.menu_id,
                    title=chapter_option.title,
                )
                section_by_title = {}
                hierarchy = (chapter, section_by_title)
                hierarchy_by_title[chapter_key] = hierarchy
                chapters.append(chapter)
            else:
                chapter, section_by_title = hierarchy

            section_key = _matching_key(section_option.title)
            section = section_by_title.get(section_key)
            if section is None:
                section = Section(
                    section_id=section_option.menu_id,
                    title=section_option.title,
                )
                section_by_title[section_key] = section
                chapter.sections.append(section)

            for source_deck_id in source_deck_ids:
                section.flashcards.extend(
                    deck_loader(
                        menu_id=source_deck_id,
                        chapter_id=chapter.chapter_id,
                        section_id=section.section_id,
                        chapter_title=chapter.title,
                        section_title=section.title,
                        timeout=timeout,
                    )
                )


def get_flashcards_for_book(
    book_id: int,
    book_title: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Deck:
    """Return Flashcards and Audio cards in one matched hierarchy."""
    if not isinstance(book_id, int) or isinstance(book_id, bool) or book_id <= 0:
        raise ValueError("A selected book must have a positive menu ID.")
    if not isinstance(book_title, str) or not book_title.strip():
        raise ValueError("A selected book must have a title.")

    book_options = get_menu_options(book_id, timeout)
    chapters = []
    hierarchy_by_title = {}
    source_specs = (
        (
            FLASHCARDS_MENU_TITLE,
            STUDY_MODE_DECK_TYPE,
            get_flashcard_deck,
        ),
        (
            AUDIO_MENU_TITLE,
            RECORD_YOURSELF_DECK_TYPE,
            get_audio_deck,
        ),
    )
    found_content_menu = False

    for menu_title, deck_type, deck_loader in source_specs:
        source_menus = [
            option
            for option in book_options
            if option.title.casefold() == menu_title.casefold()
        ]
        found_content_menu = found_content_menu or bool(source_menus)
        for source_menu in source_menus:
            _merge_source_menu(
                source_menu,
                deck_type,
                deck_loader,
                timeout,
                chapters,
                hierarchy_by_title,
            )

    if not found_content_menu:
        raise ValueError(
            "The selected book does not have a Flashcards or Audio menu."
        )

    if not chapters:
        raise ValueError(
            "The selected book does not have any Flashcards or Audio cards."
        )

    return Deck(title=book_title, chapters=chapters)


def flashcards_to_json(flashcards: Iterable[Flashcard]) -> str:
    """Format flashcards as readable JSON with Anki note field names."""
    return json.dumps(
        [flashcard.anki_fields() for flashcard in flashcards],
        ensure_ascii=False,
        indent=2,
    )
