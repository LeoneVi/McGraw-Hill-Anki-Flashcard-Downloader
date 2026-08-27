"""List the languages and books available in the Language Lab menus."""

from language_lab_api import (
    DEFAULT_TIMEOUT_SECONDS,
    MenuOption,
    get_menu_options,
)


ROOT_MENU_ID = 0


def get_language_options(
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[MenuOption]:
    """Return root languages, replacing Other with its language submenu."""
    languages = []

    for option in get_menu_options(ROOT_MENU_ID, timeout):
        if option.title != "Other":
            languages.append(option)
            continue

        languages.extend(get_menu_options(option.menu_id, timeout))

    return languages


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
