"""Shared access to the McGraw-Hill Language Lab menu API."""

from dataclasses import dataclass
import json
import ssl
import urllib.request

import certifi


MENU_URL_TEMPLATE = (
    "https://mhe-language-lab.azurewebsites.net/api/GetSubMenus?parentID={parent_id}"
)
DEFAULT_TIMEOUT_SECONDS = 10
HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


@dataclass(frozen=True)
class MenuOption:
    """One selectable item returned by a Language Lab menu."""

    menu_id: int
    title: str
    deck_type: str | None = None


def get_json(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS):
    """Download and decode one JSON response from the Language Lab API."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "McGraw-Hill-Anki-Flashcard-Download/0.1"},
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=HTTPS_CONTEXT,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def get_menu_options(
    parent_id: int,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[MenuOption]:
    """Download and validate the child menu for a parent menu ID."""
    if not isinstance(parent_id, int) or isinstance(parent_id, bool):
        raise ValueError("A menu parent ID must be an integer.")

    url = MENU_URL_TEMPLATE.format(parent_id=parent_id)
    payload = get_json(url, timeout)

    if not isinstance(payload, list):
        raise ValueError("Expected the menu API to return a list.")

    menu_options = []
    for option in payload:
        if (
            not isinstance(option, dict)
            or not isinstance(option.get("Menu_ID"), int)
            or isinstance(option.get("Menu_ID"), bool)
        ):
            raise ValueError("A menu option is missing a valid Menu_ID.")
        if not isinstance(option.get("MenuTitle"), str):
            raise ValueError("A menu option is missing a valid MenuTitle.")

        deck_type = option.get("DeckType")
        if deck_type is not None and not isinstance(deck_type, str):
            raise ValueError("A menu option has an invalid DeckType.")

        menu_options.append(
            MenuOption(
                menu_id=option["Menu_ID"],
                title=option["MenuTitle"],
                deck_type=deck_type,
            )
        )

    return menu_options
