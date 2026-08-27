from pathlib import Path
import zipfile

import pytest

from anki.collection import (
    Collection,
    ImportAnkiPackageOptions,
    ImportAnkiPackageRequest,
)
from create_anki_deck import create_anki_package, package_filename
from flashcard_models import Card, Chapter, Deck, Flashcard, Section


def make_pmp_basic_german_deck() -> Deck:
    flashcard = Flashcard(
        Card(
            card_id=354760,
            side_a="ich",
            side_b="I",
            side_a_audio=None,
            side_b_audio=None,
            chapter_id=1550,
            section_id=11267,
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
        finally:
            collection.close()

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
