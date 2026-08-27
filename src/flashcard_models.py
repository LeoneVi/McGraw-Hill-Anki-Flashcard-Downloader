"""Domain objects for scraped cards and their book hierarchy."""

from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Card:
    """One raw McGraw-Hill card with its source metadata."""

    card_id: int
    side_a: str
    side_b: str
    side_a_audio: str | None
    side_b_audio: str | None
    chapter_id: int
    section_id: int
    chapter_title: str
    section_title: str
    tts_audio: bool = False
    side_a_language: str | None = None
    side_b_language: str | None = None
    tts_side_a: str | None = None
    tts_side_b: str | None = None


@dataclass(frozen=True)
class Flashcard:
    """An Anki-facing view of one raw McGraw-Hill card."""

    card: Card

    @property
    def front(self) -> str:
        return self.card.side_a

    @property
    def back(self) -> str:
        return self.card.side_b

    @property
    def front_audio(self) -> str | None:
        return self.card.side_a_audio

    @property
    def back_audio(self) -> str | None:
        return self.card.side_b_audio

    def anki_fields(self) -> dict[str, str]:
        """Return the note fields stored in the generated Anki package."""
        return {
            "Front": self.front,
            "Back": self.back,
            "SideAAudio": self.front_audio or "",
            "SideBAudio": self.back_audio or "",
            "SourceCardID": str(self.card.card_id),
            "Chapter": self.card.chapter_title,
            "Section": self.card.section_title,
            "ChapterID": str(self.card.chapter_id),
            "SectionID": str(self.card.section_id),
        }


@dataclass
class Section:
    """A book section containing its flashcards."""

    section_id: int
    title: str
    flashcards: list[Flashcard] = field(default_factory=list)

    @property
    def cards(self) -> list[Card]:
        return [flashcard.card for flashcard in self.flashcards]


@dataclass
class Chapter:
    """A book chapter containing sections."""

    chapter_id: int
    title: str
    sections: list[Section] = field(default_factory=list)

    def iter_flashcards(self) -> Iterator[Flashcard]:
        for section in self.sections:
            yield from section.flashcards


@dataclass
class Deck:
    """A scraped book organized as chapters, sections, and flashcards."""

    title: str
    chapters: list[Chapter] = field(default_factory=list)

    def iter_flashcards(self) -> Iterator[Flashcard]:
        for chapter in self.chapters:
            yield from chapter.iter_flashcards()

    @property
    def flashcards(self) -> list[Flashcard]:
        return list(self.iter_flashcards())

    @property
    def cards(self) -> list[Card]:
        return [flashcard.card for flashcard in self.iter_flashcards()]

    @property
    def card_count(self) -> int:
        return sum(1 for _ in self.iter_flashcards())
