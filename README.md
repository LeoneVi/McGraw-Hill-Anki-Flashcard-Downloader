# McGraw-Hill Language Lab Anki Flashcard Downloader

Create an importable Anki deck from a book in the McGraw-Hill Language Lab. The program provides an interactive terminal menu for choosing a language, choosing a book, configuring text-to-speech, and selecting where the finished `.apkg` file should be saved.

## Requirements

- Python 3.11
- An internet connection while scraping and downloading recorded audio
- A terminal that supports interactive keyboard input
- [Anki Desktop](https://apps.ankiweb.net/) to import and use the generated deck

The terminal interface is designed for macOS and Linux.

## Build and set up the project

Clone this repo, create a virtual environment, and install its dependencies.

```bash
git clone https://github.com/LeoneVi/McGraw-Hill-Anki-Flashcard-Downloader.git
cd McGraw-Hill-Anki-Flashcard-Downloader
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

To install the test dependencies as well, use:

```bash
python -m pip install -r requirements-dev.txt
```

## Use the downloader

From the project root, run:

```bash
source .venv/bin/activate
python src/main.py
```

The program will guide you through the following choices:

1. Select the language you want to study with the Up and Down arrow keys, then press Enter.
2. Select a book. The book menu also lets you return to the language menu.
3. Select which sides should use generated TTS:
   - `Only German`, for example, adds TTS only to the language being studied.
   - `Both German and my language` adds TTS to both sides when the source card permits it.
4. Type an output directory, or press Enter to use the project's `output` directory.
5. Wait while the terminal displays the current chapter, section, card count, and package progress.

The selected language is retained throughout the run and is used for the book menu, TTS choice, and final summary.

The default result is:

```text
output/Book_Title.apkg
```

Import that `.apkg` file into Anki with **File → Import**.

## Run the tests

Install the development requirements, then run all tests from the project root:

```bash
.venv/bin/python -m pytest
```

PyCharm can also discover the tests in the `tests` directory and display each pytest class, test case, result, and failure message in its test runner.

## Special features

- **Flashcards and Audio scraping:** The scraper reads both areas of a Language Lab book instead of limiting the deck to the Flashcards menu.
- **Configurable TTS sides:** Generate TTS for only the language being studied or for both the studied language and the translation.
- **Instruction propagation:** If the first card in an exercise contains directions, the directions are retained and shown in italics above every card in that exercise.
- **Human-readable organization:** Cards retain their chapter and section labels and receive readable Anki tags for chapter, section, and source.
- **Visible progress:** The terminal reports scraping locations, processed card counts, percentages, media work, and final package creation.
- **Downloadable Anki packages:** Output is a modern `.apkg` file that can be imported directly into Anki.

## Project structure

```text
src/
  main.py                    Interactive terminal workflow
  scrape_language_menus.py  Language and book menu scraping
  scrape_flashcards.py      Flashcard, audio, chapter, and section scraping
  flashcard_models.py       Card, section, chapter, and deck objects
  create_anki_deck.py       Anki note and package generation
  language_lab_api.py       Shared HTTP and menu API access
  progress_reporting.py     Shared terminal progress display
tests/                       Pytest unit and package-integration tests
output/                      Generated decks
```

## Problems and feature requests

If something fails, a book has an unexpected layout, audio is missing, or you have an idea for an improvement, please [open a GitHub issue](https://github.com/LeoneVi/McGraw-Hill-Anki-Flashcard-Downloader/issues).

When reporting a problem, include the selected language, book title, operating system, Python version, and the complete error message when possible.
