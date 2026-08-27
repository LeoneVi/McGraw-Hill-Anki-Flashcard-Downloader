import io
import json
import ssl
import urllib.error

import pytest

import scraper


class TestLanguageSelection:
    def test_expands_other_into_its_language_submenu(self, monkeypatch):
        root_payload = [
            {"Menu_ID": 1, "MenuTitle": "English (ESL)"},
            {"Menu_ID": 2, "MenuTitle": "French"},
            {"Menu_ID": 3, "MenuTitle": "German"},
            {"Menu_ID": 4, "MenuTitle": "Italian"},
            {"Menu_ID": 5, "MenuTitle": "Spanish"},
            {"Menu_ID": 6, "MenuTitle": "Other"},
        ]
        other_payload = [
            {"Menu_ID": 83487, "MenuTitle": "Arabic"},
            {"Menu_ID": 83491, "MenuTitle": "Chinese"},
            {"Menu_ID": 83489, "MenuTitle": "Japanese"},
            {"Menu_ID": 83490, "MenuTitle": "Korean"},
            {"Menu_ID": 86381, "MenuTitle": "Portuguese"},
            {"Menu_ID": 136797, "MenuTitle": "Russian"},
        ]
        captured_requests = []

        def fake_urlopen(request, timeout, context):
            captured_requests.append((request.full_url, timeout, context))
            if request.full_url == scraper.LANGUAGE_MENU_URL:
                payload = root_payload
            else:
                payload = other_payload
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        monkeypatch.setattr(scraper.urllib.request, "urlopen", fake_urlopen)

        result = scraper.get_language_options()

        assert result == [
            "English (ESL)",
            "French",
            "German",
            "Italian",
            "Spanish",
            "Arabic",
            "Chinese",
            "Japanese",
            "Korean",
            "Portuguese",
            "Russian",
        ]
        assert "Other" not in result
        assert captured_requests == [
            (
                scraper.LANGUAGE_MENU_URL,
                scraper.DEFAULT_TIMEOUT_SECONDS,
                scraper.HTTPS_CONTEXT,
            ),
            (
                scraper.MENU_URL_TEMPLATE.format(parent_id=6),
                scraper.DEFAULT_TIMEOUT_SECONDS,
                scraper.HTTPS_CONTEXT,
            ),
        ]
        assert scraper.HTTPS_CONTEXT.check_hostname is True
        assert scraper.HTTPS_CONTEXT.verify_mode == ssl.CERT_REQUIRED

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            pytest.param(
                {"MenuTitle": "Spanish"},
                "return a list",
                id="top-level-payload-is-not-a-list",
            ),
            pytest.param(
                [{"Menu_ID": 1}],
                "valid MenuTitle",
                id="language-option-has-no-title",
            ),
            pytest.param(
                [{"MenuTitle": "Other"}],
                "valid Menu_ID",
                id="other-menu-has-no-id",
            ),
        ],
    )
    def test_rejects_invalid_api_data(self, monkeypatch, payload, message):
        def fake_urlopen(request, timeout, context):
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        monkeypatch.setattr(scraper.urllib.request, "urlopen", fake_urlopen)

        with pytest.raises(ValueError, match=message):
            scraper.get_language_options()

    def test_reports_network_errors(self, monkeypatch):
        def raise_network_error(request, timeout, context):
            raise urllib.error.URLError("offline")

        monkeypatch.setattr(
            scraper.urllib.request,
            "urlopen",
            raise_network_error,
        )

        with pytest.raises(urllib.error.URLError, match="offline"):
            scraper.get_language_options()

    def test_prints_one_language_per_line(self, monkeypatch, capsys):
        monkeypatch.setattr(
            scraper,
            "get_language_options",
            lambda: ["English (ESL)", "Spanish", "Arabic"],
        )

        scraper.main()

        assert capsys.readouterr().out == "English (ESL)\nSpanish\nArabic\n"
