from pathlib import Path
import urllib.error
import zipfile

import pytest

from anki.collection import (
    Collection,
    ImportAnkiPackageOptions,
    ImportAnkiPackageRequest,
)
from anki.sound import SoundOrVideoTag, TTSTag
import create_anki_deck as creator
from create_anki_deck import create_anki_package, package_filename
from flashcard_models import Card, Chapter, Deck, Flashcard, Section


def make_pmp_basic_german_deck(
    side_a_audio: str | None = None,
    tts_audio: bool = True,
) -> Deck:
    flashcard = Flashcard(
        Card(
            card_id=354760,
            side_a="ich",
            side_b="I",
            side_a_audio=side_a_audio,
            side_b_audio=None,
            chapter_id=1550,
            section_id=11267,
            chapter_title="2. Vowel combinations and consonant combinations",
            section_title="Wortschatz (p.9)",
            tts_audio=tts_audio,
            side_a_language="de-DE",
            side_b_language="en-US",
        )
    )
    return Deck(
        title="PMP Basic German",
        chapters=[
            Chapter(
                chapter_id=1550,
                title="2. Vowel combinations and consonant combinations",
                sections=[
                    Section(
                        section_id=11267,
                        title="Wortschatz (p.9)",
                        flashcards=[flashcard],
                    )
                ],
            )
        ],
    )


class TestCreateAnkiDeck:
    def test_creates_a_real_downloadable_apkg(self, tmp_path):
        destination = tmp_path / "PMP_Basic_German.apkg"

        result = create_anki_package(
            make_pmp_basic_german_deck(),
            destination,
        )

        assert result == destination.resolve()
        assert zipfile.is_zipfile(result)
        with zipfile.ZipFile(result) as package:
            assert {"collection.anki21b", "media", "meta"}.issubset(
                package.namelist()
            )

        collection = Collection(str(tmp_path / "verify.anki2"))
        try:
            request = ImportAnkiPackageRequest(
                package_path=str(result),
                options=ImportAnkiPackageOptions(
                    merge_notetypes=True,
                    with_scheduling=False,
                    with_deck_configs=False,
                ),
            )
            collection.import_anki_package(request)

            assert collection.note_count() == 1
            assert collection.card_count() == 1
            assert collection.decks.id_for_name("PMP Basic German") is not None

            note = collection.get_note(collection.find_notes("")[0])
            assert note["Front"] == "ich"
            assert note["Back"] == "I"
            assert note["SideAAudio"] == (
                "[anki:tts lang=de_DE]ich[/anki:tts]"
            )
            assert note["SideBAudio"] == (
                "[anki:tts lang=en_US]I[/anki:tts]"
            )
            assert note["Chapter"] == (
                "2. Vowel combinations and consonant combinations"
            )
            assert note["Section"] == "Wortschatz (p.9)"
            assert set(note.tags) == {
                "mhe::chapter::2._Vowel_combinations_and_consonant_combinations",
                "mhe::section::Wortschatz_(p.9)",
            }

            template = note.note_type()["tmpls"][0]
            assert template["qfmt"] == "{{Front}}{{SideAAudio}}"
            assert template["afmt"] == (
                "{{FrontSide}}<hr id=answer>{{Back}}{{SideBAudio}}"
            )

            card = note.cards()[0]
            assert card.question_av_tags() == [
                TTSTag(
                    field_text="ich",
                    lang="de_DE",
                    voices=[],
                    speed=1.0,
                    other_args=[],
                )
            ]
            assert card.answer_av_tags() == [
                TTSTag(
                    field_text="I",
                    lang="en_US",
                    voices=[],
                    speed=1.0,
                    other_args=[],
                )
            ]
        finally:
            collection.close()

    def test_downloads_packages_and_references_recorded_audio(
        self,
        monkeypatch,
        tmp_path,
    ):
        audio_bytes = b"ID3\x04\x00\x00test-mp3-data"
        captured_download = {}

        def fake_get_bytes(url, timeout):
            captured_download["url"] = url
            captured_download["timeout"] = timeout
            return audio_bytes

        monkeypatch.setattr(creator, "get_bytes", fake_get_bytes)
        result = create_anki_package(
            make_pmp_basic_german_deck(
                side_a_audio="https://example.com/audio/ich.mp3",
                tts_audio=False,
            ),
            tmp_path / "recorded.apkg",
        )

        assert captured_download == {
            "url": "https://example.com/audio/ich.mp3",
            "timeout": creator.DEFAULT_TIMEOUT_SECONDS,
        }

        collection = Collection(str(tmp_path / "recorded-verify.anki2"))
        try:
            collection.import_anki_package(
                ImportAnkiPackageRequest(
                    package_path=str(result),
                    options=ImportAnkiPackageOptions(
                        merge_notetypes=True,
                        with_scheduling=False,
                        with_deck_configs=False,
                    ),
                )
            )
            note = collection.get_note(collection.find_notes("")[0])
            filename = "mhe_354760_side_a.mp3"

            assert note["SideAAudio"] == f"[sound:{filename}]"
            assert note["SideBAudio"] == ""
            assert note.cards()[0].question_av_tags() == [
                SoundOrVideoTag(filename=filename)
            ]
            media_path = Path(collection.media.dir()) / filename
            assert media_path.is_file()
            assert media_path.read_bytes() == audio_bytes
            assert collection.media.check().missing == []
        finally:
            collection.close()

    def test_does_not_silently_drop_failed_recorded_audio(
        self,
        monkeypatch,
        tmp_path,
    ):
        def raise_network_error(url, timeout):
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(creator, "get_bytes", raise_network_error)

        with pytest.raises(urllib.error.URLError, match="offline"):
            create_anki_package(
                make_pmp_basic_german_deck(
                    side_a_audio="https://example.com/audio/ich.mp3",
                    tts_audio=False,
                ),
                tmp_path / "download-failed.apkg",
            )

        assert not (tmp_path / "download-failed.apkg").exists()

    def test_rejects_an_empty_deck(self, tmp_path):
        with pytest.raises(ValueError, match="empty deck"):
            create_anki_package(
                Deck(title="PMP Basic German"),
                tmp_path / "empty.apkg",
            )

    def test_requires_the_apkg_extension(self, tmp_path):
        with pytest.raises(ValueError, match=".apkg extension"):
            create_anki_package(
                make_pmp_basic_german_deck(),
                tmp_path / "deck.zip",
            )

    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("PMP Basic German", "PMP_Basic_German.apkg"),
            ("German: A/B", "German_A_B.apkg"),
        ],
    )
    def test_creates_safe_package_filenames(self, title, expected):
        assert package_filename(title) == expected
