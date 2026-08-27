import io
import json
import ssl
import urllib.error

import pytest

import language_lab_api as api


class TestLanguageLabApi:
    def test_fetches_and_converts_a_child_menu(self, monkeypatch):
        payload = [
            {"Menu_ID": 43, "MenuTitle": "Complete Medical Spanish"},
            {"Menu_ID": 50, "MenuTitle": "Complete Spanish Step-by-Step"},
        ]
        captured_request = {}

        def fake_urlopen(request, timeout, context):
            captured_request["url"] = request.full_url
            captured_request["timeout"] = timeout
            captured_request["context"] = context
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        monkeypatch.setattr(api.urllib.request, "urlopen", fake_urlopen)

        result = api.get_menu_options(parent_id=5)

        assert result == [
            api.MenuOption(43, "Complete Medical Spanish"),
            api.MenuOption(50, "Complete Spanish Step-by-Step"),
        ]
        assert captured_request == {
            "url": api.MENU_URL_TEMPLATE.format(parent_id=5),
            "timeout": api.DEFAULT_TIMEOUT_SECONDS,
            "context": api.HTTPS_CONTEXT,
        }
        assert api.HTTPS_CONTEXT.check_hostname is True
        assert api.HTTPS_CONTEXT.verify_mode == ssl.CERT_REQUIRED

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            pytest.param(
                {"MenuTitle": "Spanish"},
                "return a list",
                id="top-level-payload-is-not-a-list",
            ),
            pytest.param(
                [{"MenuTitle": "Spanish"}],
                "valid Menu_ID",
                id="menu-option-has-no-id",
            ),
            pytest.param(
                [{"Menu_ID": 5}],
                "valid MenuTitle",
                id="menu-option-has-no-title",
            ),
        ],
    )
    def test_rejects_invalid_api_data(self, monkeypatch, payload, message):
        def fake_urlopen(request, timeout, context):
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        monkeypatch.setattr(api.urllib.request, "urlopen", fake_urlopen)

        with pytest.raises(ValueError, match=message):
            api.get_menu_options(parent_id=5)

    def test_reports_network_errors(self, monkeypatch):
        def raise_network_error(request, timeout, context):
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(api.urllib.request, "urlopen", raise_network_error)

        with pytest.raises(urllib.error.URLError, match="offline"):
            api.get_menu_options(parent_id=5)
