"""Scrape a selected Language Lab book into a structured deck."""

from collections.abc import Iterable
import json

from flashcard_models import Card, Chapter, Deck, Flashcard, Section
from language_lab_api import (
    DEFAULT_TIMEOUT_SECONDS,
    get_json,
    get_menu_options,
)


FLASHCARD_URL_TEMPLATE = (
    "https://mhe-language-lab.azurewebsites.net/api/GetFlashCards?menuID={menu_id}"
)
FLASHCARDS_MENU_TITLE = "Flashcards"
STUDY_MODE_DECK_TYPE = "Flashcards: Study Mode"


def _optional_text(record: dict, field_name: str) -> str | None:
    value = record.get(field_name)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"A flashcard has invalid {field_name} data.")
    return value


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

    url = FLASHCARD_URL_TEMPLATE.format(menu_id=menu_id)
    payload = get_json(url, timeout)

    if not isinstance(payload, list):
        raise ValueError("Expected the flashcard API to return a list.")

    flashcards = []
    for card_data in payload:
        if (
            not isinstance(card_data, dict)
            or not isinstance(card_data.get("Card_ID"), int)
            or isinstance(card_data.get("Card_ID"), bool)
        ):
            raise ValueError("A flashcard is missing a valid Card_ID.")
        if not isinstance(card_data.get("SideA"), str):
            raise ValueError("A flashcard is missing valid SideA text.")
        if not isinstance(card_data.get("SideB"), str):
            raise ValueError("A flashcard is missing valid SideB text.")

        card = Card(
            card_id=card_data["Card_ID"],
            side_a=card_data["SideA"],
            side_b=card_data["SideB"],
            side_a_audio=_optional_text(card_data, "SideAAudio"),
            side_b_audio=_optional_text(card_data, "SideBAudio"),
            chapter_id=chapter_id,
            section_id=section_id,
            chapter_title=chapter_title,
            section_title=section_title,
        )
        flashcards.append(Flashcard(card=card))

    return flashcards


def _find_study_deck_ids(
    parent_id: int,
    timeout: int,
    visited_menu_ids: set[int],
) -> list[int]:
    """Recursively find study-mode decks below a section menu."""
    if parent_id in visited_menu_ids:
        return []
    visited_menu_ids.add(parent_id)

    study_deck_ids = []
    for option in get_menu_options(parent_id, timeout):
        if option.deck_type == STUDY_MODE_DECK_TYPE:
            study_deck_ids.append(option.menu_id)
            continue

        if option.deck_type in (None, "N/A"):
            study_deck_ids.extend(
                _find_study_deck_ids(
                    option.menu_id,
                    timeout,
                    visited_menu_ids,
                )
            )

    return study_deck_ids


def get_flashcards_for_book(
    book_id: int,
    book_title: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Deck:
    """Return a book organized into chapters, sections, and flashcards."""
    if not isinstance(book_id, int) or isinstance(book_id, bool) or book_id <= 0:
        raise ValueError("A selected book must have a positive menu ID.")
    if not isinstance(book_title, str) or not book_title.strip():
        raise ValueError("A selected book must have a title.")

    book_options = get_menu_options(book_id, timeout)
    flashcard_menus = [
        option
        for option in book_options
        if option.title.casefold() == FLASHCARDS_MENU_TITLE.casefold()
    ]
    if not flashcard_menus:
        raise ValueError("The selected book does not have a Flashcards menu.")

    chapters = []
    for flashcard_menu in flashcard_menus:
        for chapter_option in get_menu_options(flashcard_menu.menu_id, timeout):
            sections = []
            for section_option in get_menu_options(chapter_option.menu_id, timeout):
                study_deck_ids = _find_study_deck_ids(
                    section_option.menu_id,
                    timeout,
                    set(),
                )
                section_flashcards = []
                for study_deck_id in study_deck_ids:
                    section_flashcards.extend(
                        get_flashcard_deck(
                            menu_id=study_deck_id,
                            chapter_id=chapter_option.menu_id,
                            section_id=section_option.menu_id,
                            chapter_title=chapter_option.title,
                            section_title=section_option.title,
                            timeout=timeout,
                        )
                    )

                if section_flashcards:
                    sections.append(
                        Section(
                            section_id=section_option.menu_id,
                            title=section_option.title,
                            flashcards=section_flashcards,
                        )
                    )

            if sections:
                chapters.append(
                    Chapter(
                        chapter_id=chapter_option.menu_id,
                        title=chapter_option.title,
                        sections=sections,
                    )
                )

    if not chapters:
        raise ValueError("The selected book does not have any study flashcards.")

    return Deck(title=book_title, chapters=chapters)


def flashcards_to_json(flashcards: Iterable[Flashcard]) -> str:
    """Format flashcards as readable JSON with Anki note field names."""
    return json.dumps(
        [flashcard.anki_fields() for flashcard in flashcards],
        ensure_ascii=False,
        indent=2,
    )
