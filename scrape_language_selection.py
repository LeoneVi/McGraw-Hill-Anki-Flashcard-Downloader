"""List the language options shown on the Language Lab home page."""

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
