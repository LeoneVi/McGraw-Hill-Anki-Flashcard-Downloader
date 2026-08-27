"""List the language options shown on the McGraw-Hill Language Lab home page."""

import json
import ssl
import urllib.request

import certifi


MENU_URL_TEMPLATE = (
    "https://mhe-language-lab.azurewebsites.net/api/GetSubMenus?parentID={parent_id}"
)
LANGUAGE_MENU_URL = MENU_URL_TEMPLATE.format(parent_id=0)
DEFAULT_TIMEOUT_SECONDS = 10
HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def _get_menu_options(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[dict]:
    """Fetch and validate one menu from the Language Lab API."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "McGraw-Hill-Anki-Flashcard-Download/0.1"},
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=HTTPS_CONTEXT,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, list):
        raise ValueError("Expected the menu API to return a list.")

    for option in payload:
        if not isinstance(option, dict) or not isinstance(
            option.get("MenuTitle"), str
        ):
            raise ValueError("A menu option is missing a valid MenuTitle.")

    return payload


def get_language_options(
    url: str = LANGUAGE_MENU_URL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> list[str]:
    """Return root languages, replacing Other with its language submenu."""
    languages = []

    for option in _get_menu_options(url, timeout):
        if option["MenuTitle"] != "Other":
            languages.append(option["MenuTitle"])
            continue

        other_menu_id = option.get("Menu_ID")
        if not isinstance(other_menu_id, int):
            raise ValueError("The Other menu is missing a valid Menu_ID.")

        other_menu_url = MENU_URL_TEMPLATE.format(parent_id=other_menu_id)
        other_options = _get_menu_options(other_menu_url, timeout)
        languages.extend(option["MenuTitle"] for option in other_options)

    return languages


def main() -> None:
    """Print one home-page language option per line."""
    for language in get_language_options():
        print(language)


if __name__ == "__main__":
    main()
