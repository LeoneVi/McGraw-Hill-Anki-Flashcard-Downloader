"""Create a downloadable Anki deck package from a scraped deck."""

import hashlib
from enum import Enum
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from anki.collection import (
    Collection,
    DeckIdLimit,
    ExportAnkiPackageOptions,
)
from anki.decks import DeckId
from anki.utils import base91

from flashcard_models import Deck, Flashcard
from language_lab_api import DEFAULT_TIMEOUT_SECONDS, get_bytes
from progress_reporting import ProgressCallback, report_progress


NOTETYPE_NAME = "McGraw-Hill Language Lab"
NOTETYPE_FIELDS = (
    "Front",
    "Back",
    "Instruction",
    "SideAAudio",
    "SideBAudio",
    "SourceCardID",
    "Chapter",
    "Section",
    "ChapterID",
    "SectionID",
    "Source",
)


class TTSAudioMode(Enum):
    """Choose which translated sides receive generated Anki TTS."""

    SELECTED_LANGUAGE_ONLY = "selected_language_only"
    BOTH_LANGUAGES = "both_languages"


def package_filename(deck_title: str) -> str:
    """Return a filesystem-safe .apkg filename for a deck title."""
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", deck_title).strip("._")
    return f"{safe_title or 'language_lab_deck'}.apkg"


def _stable_integer_id(namespace: str, value: str) -> int:
    digest = hashlib.blake2b(
        f"{namespace}:{value}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return max(2, int.from_bytes(digest, "big") & ((1 << 63) - 1))


def _stable_note_guid(flashcard: Flashcard) -> str:
    note_id = _stable_integer_id("mhe-card", str(flashcard.card.card_id))
    return base91(note_id)


def _anki_tag_component(label: str) -> str:
    """Keep a source label readable while making it one valid Anki tag."""
    return re.sub(r"\s+", "_", label.strip()).replace("::", "_")


def _media_filename(flashcard: Flashcard, side: str, url: str) -> str:
    extension = Path(urlsplit(url).path).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", extension):
        extension = ".mp3"
    return f"mhe_{flashcard.card.card_id}_side_{side}{extension}"


def _tts_reference(text: str, language: str | None) -> str:
    if not language:
        raise ValueError("A TTS-enabled flashcard is missing its language.")

    anki_language = language.replace("-", "_")
    if not re.fullmatch(r"[A-Za-z0-9_]+", anki_language):
        raise ValueError(f"A flashcard has an invalid TTS language: {language}")

    return f"[anki:tts lang={anki_language}]{text}[/anki:tts]"


def _audio_reference(
    collection: Collection,
    flashcard: Flashcard,
    side: str,
    timeout: int,
    downloaded_audio: dict[str, str],
    tts_mode: TTSAudioMode,
) -> str:
    card = flashcard.card
    if side == "a":
        audio_url = card.side_a_audio
        language = card.side_a_language
        tts_text = (
            card.tts_side_a if card.tts_side_a is not None else flashcard.front
        )
    else:
        audio_url = card.side_b_audio
        language = card.side_b_language
        tts_text = card.tts_side_b if card.tts_side_b is not None else card.side_b

    if audio_url:
        filename = downloaded_audio.get(audio_url)
        if filename is None:
            audio_data = get_bytes(audio_url, timeout)
            if not audio_data:
                raise ValueError(f"Downloaded empty audio for card {card.card_id}.")
            filename = collection.media.write_data(
                _media_filename(flashcard, side, audio_url),
                audio_data,
            )
            downloaded_audio[audio_url] = filename
        return f"[sound:{filename}]"

    # Language Lab places the language being studied on Side A and the
    # learner's translation on Side B. Recorded audio is retained above,
    # regardless of this TTS preference.
    tts_is_selected = side == "a" or tts_mode is TTSAudioMode.BOTH_LANGUAGES
    if card.tts_audio and tts_is_selected:
        return _tts_reference(tts_text, language)

    return ""


def _create_notetype(collection: Collection):
    notetype = collection.models.new(NOTETYPE_NAME)
    for field_name in NOTETYPE_FIELDS:
        field = collection.models.new_field(field_name)
        collection.models.add_field(notetype, field)

    template = collection.models.new_template("Front to Back")
    template["qfmt"] = (
        '{{#Instruction}}<div class="instruction">{{Instruction}}</div>'
        "{{/Instruction}}{{Front}}{{SideAAudio}}"
    )
    template["afmt"] = (
        "{{FrontSide}}<hr id=answer>{{Back}}{{SideBAudio}}"
    )
    collection.models.add_template(notetype, template)

    notetype["css"] += """
.instruction {
    margin-bottom: 1em;
    font-style: italic;
}
"""

    notetype["id"] = _stable_integer_id("notetype", NOTETYPE_NAME)
    collection.models.update(notetype)
    return notetype


def _create_deck(collection: Collection, title: str) -> DeckId:
    deck = collection.decks.new_deck_legacy(filtered=False)
    deck["id"] = _stable_integer_id("deck", title)
    deck["name"] = title
    collection.decks.update(deck)
    return DeckId(deck["id"])


def _add_flashcard_note(
    collection: Collection,
    notetype,
    deck_id: DeckId,
    flashcard: Flashcard,
    timeout: int,
    downloaded_audio: dict[str, str],
    tts_mode: TTSAudioMode,
) -> None:
    note = collection.new_note(notetype)
    fields = flashcard.anki_fields()
    fields["SideAAudio"] = _audio_reference(
        collection,
        flashcard,
        "a",
        timeout,
        downloaded_audio,
        tts_mode,
    )
    fields["SideBAudio"] = _audio_reference(
        collection,
        flashcard,
        "b",
        timeout,
        downloaded_audio,
        tts_mode,
    )
    for field_name, value in fields.items():
        note[field_name] = value

    note.guid = _stable_note_guid(flashcard)
    note.tags = [
        f"mhe::chapter::{_anki_tag_component(flashcard.card.chapter_title)}",
        f"mhe::section::{_anki_tag_component(flashcard.card.section_title)}",
        f"mhe::source::{_anki_tag_component(flashcard.card.source)}",
    ]
    collection.add_note(note, deck_id)


def create_anki_package(
    deck: Deck,
    output_path: str | Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    tts_mode: TTSAudioMode = TTSAudioMode.BOTH_LANGUAGES,
    progress_callback: ProgressCallback | None = None,
) -> Path:
    """Create a modern .apkg file and return its absolute path."""
    if deck.card_count == 0:
        raise ValueError("Cannot create an Anki package from an empty deck.")
    if not isinstance(tts_mode, TTSAudioMode):
        raise ValueError("A valid TTS audio mode must be selected.")

    destination = Path(output_path).expanduser().resolve()
    if destination.suffix.lower() != ".apkg":
        raise ValueError("An Anki deck package must use the .apkg extension.")
    destination.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix="mhe-anki-") as temporary_directory:
        collection_path = Path(temporary_directory) / "source.anki2"
        collection = Collection(str(collection_path))
        try:
            notetype = _create_notetype(collection)
            deck_id = _create_deck(collection, deck.title)
            downloaded_audio = {}
            total_cards = deck.card_count
            progress_interval = max(1, total_cards // 100)

            report_progress(
                progress_callback,
                f"Creating Anki package: 0/{total_cards} cards (0%)",
            )

            for card_number, flashcard in enumerate(
                deck.iter_flashcards(),
                start=1,
            ):
                if card_number == 1 or card_number % progress_interval == 0:
                    percentage = int((card_number - 1) * 100 / total_cards)
                    report_progress(
                        progress_callback,
                        "Creating Anki package: "
                        f"{card_number}/{total_cards} cards ({percentage}%)",
                    )
                _add_flashcard_note(
                    collection,
                    notetype,
                    deck_id,
                    flashcard,
                    timeout,
                    downloaded_audio,
                    tts_mode,
                )

            report_progress(
                progress_callback,
                f"Creating Anki package: {total_cards}/{total_cards} cards (100%)",
            )

            options = ExportAnkiPackageOptions(
                with_scheduling=False,
                with_deck_configs=False,
                with_media=True,
                legacy=False,
            )
            report_progress(progress_callback, "Finalizing Anki package...")
            collection.export_anki_package(
                out_path=str(destination),
                options=options,
                limit=DeckIdLimit(deck_id),
            )
            report_progress(progress_callback, "Anki package is ready.")
        finally:
            collection.close()

    return destination
