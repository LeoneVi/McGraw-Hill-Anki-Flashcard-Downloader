"""List the books available for a selected Language Lab language."""

from language_lab_api import (
    DEFAULT_TIMEOUT_SECONDS,
    MenuOption,
    get_menu_options,
)


def get_book_options(
    language_id: int,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[MenuOption]:
    """Return the book menu belonging to a selected language."""
    if (
        not isinstance(language_id, int)
        or isinstance(language_id, bool)
        or language_id <= 0
    ):
        raise ValueError("A selected language must have a positive menu ID.")

    return get_menu_options(language_id, timeout)
