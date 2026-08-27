from flashcard_models import Card, Chapter, Deck, Flashcard, Section


def make_flashcard(
    card_id: int,
    chapter_id: int,
    section_id: int,
) -> Flashcard:
    return Flashcard(
        card=Card(
            card_id=card_id,
            side_a=f"German {card_id}",
            side_b=f"English {card_id}",
            side_a_audio=None,
            side_b_audio=None,
            chapter_id=chapter_id,
            section_id=section_id,
            chapter_title=f"Chapter {chapter_id}",
            section_title=f"Section {section_id}",
        )
    )


class TestDeckHierarchy:
    def test_keeps_the_tree_and_provides_flat_export_views(self):
        first = make_flashcard(101, 10, 11)
        second = make_flashcard(102, 20, 21)
        deck = Deck(
            title="PMP Basic German",
            chapters=[
                Chapter(
                    chapter_id=10,
                    title="Chapter 1",
                    sections=[Section(11, "Vocabulary", [first])],
                ),
                Chapter(
                    chapter_id=20,
                    title="Chapter 2",
                    sections=[Section(21, "Pronouns", [second])],
                ),
            ],
        )

        assert deck.flashcards == [first, second]
        assert deck.cards == [first.card, second.card]
        assert deck.card_count == 2

    def test_flashcard_maps_source_card_to_anki_fields(self):
        source_card = Card(
            card_id=354760,
            side_a="ich",
            side_b="I",
            side_a_audio="https://example.com/ich.mp3",
            side_b_audio=None,
            chapter_id=1550,
            section_id=11267,
            chapter_title="2. Vowel combinations and consonant combinations",
            section_title="Wortschatz (p.9)",
        )
        flashcard = Flashcard(card=source_card)

        assert flashcard.front == "ich"
        assert flashcard.back == "I"
        assert flashcard.anki_fields() == {
            "Front": "ich",
            "Back": "I",
            "SideAAudio": "https://example.com/ich.mp3",
            "SideBAudio": "",
            "SourceCardID": "354760",
            "Chapter": "2. Vowel combinations and consonant combinations",
            "Section": "Wortschatz (p.9)",
            "ChapterID": "1550",
            "SectionID": "11267",
        }
