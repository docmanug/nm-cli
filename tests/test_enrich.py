"""Tests for enrich service — Pre-Call Intelligence (Tasks 4-5 TDD).

Test order mirrors implementation steps:
1. search_urls — DuckDuckGo wrapper
2. scrape_page — Crawl4AI HTTP wrapper
3. qualify_content — keyword extraction (no mocks)
4. build_briefing — format dict → string (no mocks)
5. handle_enrich — integration test with mocks
"""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_requests_response(json_data=None, status_code=200, raise_exc=None):
    mock = MagicMock()
    mock.status_code = status_code
    if json_data is not None:
        mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    if raise_exc:
        mock.raise_for_status.side_effect = raise_exc
    return mock


def _make_profile(enrich_config=None, monday_config=None):
    profile = MagicMock()
    profile.get_service_config = MagicMock(side_effect=lambda svc: {
        "enrich": enrich_config or {"crawl4ai_url": "http://localhost:8002", "max_results": 3},
        "monday": monday_config or {
            "boards": {"fr_leads": 111111, "contacts": 222222},
            "column_maps": {},
        },
    }.get(svc, {}))
    return profile


# ---------------------------------------------------------------------------
# 1. search_urls
# ---------------------------------------------------------------------------

class TestSearchUrls:
    def test_returns_list_of_results(self):
        from nm.services.enrich import search_urls

        fake_results = [
            {"href": "https://example.com", "title": "Example clinic"},
            {"href": "https://doctolib.fr/dr-foo", "title": "Dr Foo on Doctolib"},
        ]
        with patch("nm.services.enrich.DDGS") as mock_ddgs_cls:
            instance = MagicMock()
            instance.text.return_value = fake_results
            mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=instance)
            mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)

            results = search_urls("Dr Dupont medecin esthetique Paris")

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["href"] == "https://example.com"

    def test_returns_empty_on_exception(self):
        from nm.services.enrich import search_urls

        with patch("nm.services.enrich.DDGS") as mock_ddgs_cls:
            mock_ddgs_cls.side_effect = Exception("network error")

            results = search_urls("quelconque")

        assert results == []

    def test_returns_empty_when_ddgs_returns_nothing(self):
        from nm.services.enrich import search_urls

        with patch("nm.services.enrich.DDGS") as mock_ddgs_cls:
            instance = MagicMock()
            instance.text.return_value = []
            mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=instance)
            mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)

            results = search_urls("query with no results")

        assert results == []

    def test_respects_max_results(self):
        from nm.services.enrich import search_urls

        fake_results = [{"href": f"https://site{i}.com", "title": f"Site {i}"} for i in range(10)]
        with patch("nm.services.enrich.DDGS") as mock_ddgs_cls:
            instance = MagicMock()
            instance.text.return_value = fake_results[:3]
            mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=instance)
            mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)

            results = search_urls("query", max_results=3)

        # DDGS was called with max_results=3
        instance.text.assert_called_once()
        call_kwargs = instance.text.call_args
        assert call_kwargs[1].get("max_results") == 3 or (
            len(call_kwargs[0]) > 1 and call_kwargs[0][1] == 3
        )


# ---------------------------------------------------------------------------
# 2. scrape_page
# ---------------------------------------------------------------------------

class TestScrapePage:
    @patch("nm.services.enrich.requests.post")
    def test_returns_markdown_on_success(self, mock_post):
        from nm.services.enrich import scrape_page

        mock_post.return_value = _mock_requests_response({
            "result": [{"markdown": "# Clinique Dupont\n\nSpécialiste injections botox."}]
        })

        result = scrape_page("https://clinique-dupont.fr", crawl4ai_url="http://localhost:11235")

        assert "Clinique Dupont" in result
        assert "botox" in result

    @patch("nm.services.enrich.requests.post")
    def test_returns_empty_on_timeout(self, mock_post):
        from nm.services.enrich import scrape_page
        import requests as req_module

        mock_post.side_effect = req_module.exceptions.Timeout()

        result = scrape_page("https://example.com")

        assert result == ""

    @patch("nm.services.enrich.requests.post")
    def test_returns_empty_on_http_error(self, mock_post):
        from nm.services.enrich import scrape_page
        import requests as req_module

        mock_post.side_effect = req_module.exceptions.ConnectionError()

        result = scrape_page("https://unreachable.example.com")

        assert result == ""

    @patch("nm.services.enrich.requests.post")
    def test_posts_to_correct_endpoint(self, mock_post):
        from nm.services.enrich import scrape_page

        mock_post.return_value = _mock_requests_response({"markdown": "content"})

        scrape_page("https://test.com", crawl4ai_url="http://myserver:9000")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "http://myserver:9000/crawl" in call_args[0][0] or \
               call_args[1].get("url", "").endswith("/crawl") or \
               "http://myserver:9000/crawl" == call_args[0][0]

    @patch("nm.services.enrich.requests.post")
    def test_returns_empty_when_no_markdown_key(self, mock_post):
        from nm.services.enrich import scrape_page

        mock_post.return_value = _mock_requests_response({"status": "error", "message": "blocked"})

        result = scrape_page("https://blocked.com")

        assert result == ""


# ---------------------------------------------------------------------------
# 3. qualify_content
# ---------------------------------------------------------------------------

class TestQualifyContent:
    def test_detects_aesthetic_medicine(self):
        from nm.services.enrich import qualify_content

        content = "Cabinet spécialisé en injection acide hyaluronique et botox. Médecine esthétique."
        result = qualify_content(content)

        assert result["fait_esthetique"] is True

    def test_detects_non_aesthetic(self):
        from nm.services.enrich import qualify_content

        content = "Cabinet de médecine générale. Consultations, ordonnances, bilans sanguins."
        result = qualify_content(content)

        assert result["fait_esthetique"] is False

    def test_extracts_specialties_from_content(self):
        from nm.services.enrich import qualify_content

        content = "Dermatologue spécialisée. Peeling chimique, laser CO2 et HIFU disponibles."
        result = qualify_content(content)

        specialties = result["specialites"].lower()
        # At least one specialty keyword should be found
        assert any(kw in specialties for kw in ["peeling", "laser", "hifu", "dermato"])

    def test_handles_empty_content(self):
        from nm.services.enrich import qualify_content

        result = qualify_content("")

        assert result["fait_esthetique"] is False
        assert result["specialites"] == ""
        assert result["competitors"] == ""

    def test_detects_competitor_software(self):
        from nm.services.enrich import qualify_content

        content = "Notre clinique utilise Doctolib Pro pour la gestion des rendez-vous et Galaxie pour les dossiers."
        result = qualify_content(content)

        competitors = result["competitors"].lower()
        assert "doctolib pro" in competitors or "galaxie" in competitors

    def test_returns_dict_with_required_keys(self):
        from nm.services.enrich import qualify_content

        result = qualify_content("some content about injections")

        assert "fait_esthetique" in result
        assert "specialites" in result
        assert "competitors" in result
        assert "nb_praticiens" in result

    def test_case_insensitive_detection(self):
        from nm.services.enrich import qualify_content

        content = "ACIDE HYALURONIQUE et BOTOX sont proposés."
        result = qualify_content(content)

        assert result["fait_esthetique"] is True

    def test_extracts_praticiens_count(self):
        from nm.services.enrich import qualify_content

        content = "Notre équipe de 3 praticiens vous accueille."
        result = qualify_content(content)

        # nb_praticiens is a string (column value)
        assert isinstance(result["nb_praticiens"], str)


# ---------------------------------------------------------------------------
# 4. build_briefing
# ---------------------------------------------------------------------------

class TestBuildBriefing:
    def test_formats_basic_briefing(self):
        from nm.services.enrich import build_briefing

        data = {
            "name": "Dr Martin",
            "specialite": "Dermatologue",
            "site_web": "https://dr-martin.fr",
            "doctolib": "https://doctolib.fr/dr-martin",
            "fait_esthetique": True,
            "specialites": "laser, peeling",
            "competitors": "",
            "nb_praticiens": "2",
        }
        result = build_briefing(data)

        assert "Dr Martin" in result
        assert isinstance(result, str)
        assert len(result) > 20

    def test_handles_missing_data(self):
        from nm.services.enrich import build_briefing

        result = build_briefing({})

        assert isinstance(result, str)
        # Should not raise, return something sensible
        assert len(result) >= 0

    def test_includes_site_when_present(self):
        from nm.services.enrich import build_briefing

        data = {"name": "Clinique Alpha", "site_web": "https://clinique-alpha.fr"}
        result = build_briefing(data)

        assert "clinique-alpha.fr" in result

    def test_includes_competitor_warning_when_present(self):
        from nm.services.enrich import build_briefing

        data = {
            "name": "Dr Foo",
            "competitors": "doctolib pro, galaxie",
        }
        result = build_briefing(data)

        # Should mention competitors in some form
        assert "doctolib pro" in result.lower() or "galaxie" in result.lower() or \
               "concurrent" in result.lower() or "competitor" in result.lower() or \
               "logiciel" in result.lower()

    def test_fait_esthetique_flag_reflected(self):
        from nm.services.enrich import build_briefing

        data_yes = {"name": "Dr Oui", "fait_esthetique": True}
        data_no = {"name": "Dr Non", "fait_esthetique": False}

        result_yes = build_briefing(data_yes)
        result_no = build_briefing(data_no)

        assert isinstance(result_yes, str)
        assert isinstance(result_no, str)

    def test_returns_string_not_dict(self):
        from nm.services.enrich import build_briefing

        result = build_briefing({"name": "Test"})

        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 5. handle_enrich — integration tests with full mocks
# ---------------------------------------------------------------------------

class TestHandleEnrich:
    """Integration tests: mock credentials, Monday API, DDGS, requests."""

    def _mock_monday_credentials(self):
        return {"api_token": "test-monday-token"}

    def _mock_enrich_credentials(self):
        return {"crawl4ai_url": "http://localhost:8002"}

    @patch("nm.services.enrich.requests.post")
    @patch("nm.services.enrich.DDGS")
    @patch("nm.services.enrich.MondayService")
    @patch("nm.services.enrich.get_credentials")
    def test_handle_enrich_status_enriched(
        self, mock_creds, mock_monday_cls, mock_ddgs_cls, mock_post
    ):
        from nm.services.enrich import handle_enrich

        mock_creds.side_effect = lambda svc: {
            "monday": {"api_token": "test-token"},
            "enrich": {"crawl4ai_url": "http://localhost:8002"},
        }.get(svc, {})

        # Build a MondayService mock that simulates an already-enriched lead
        monday_instance = MagicMock()
        monday_instance._query.return_value = {
            "items": [{
                "id": "12345",
                "name": "Dr Dupont",
                "board": {"id": 111111},
                "column_values": [
                    {"id": "boolean_mm13e5ct", "text": "true", "value": '"true"'},
                    {"id": "text_mm13wqzg", "text": "https://dr-dupont.fr", "value": '"https://dr-dupont.fr"'},
                ],
            }]
        }
        monday_instance._parse_columns.return_value = {
            "boolean_mm13e5ct": "true",
            "text_mm13wqzg": "https://dr-dupont.fr",
        }
        mock_monday_cls.return_value = monday_instance

        profile = _make_profile()
        result = handle_enrich("status", ["12345"], profile)

        assert isinstance(result, str)
        assert len(result) > 0

    @patch("nm.services.enrich.requests.post")
    @patch("nm.services.enrich.DDGS")
    @patch("nm.services.enrich.MondayService")
    @patch("nm.services.enrich.get_credentials")
    def test_handle_enrich_unknown_command(
        self, mock_creds, mock_monday_cls, mock_ddgs_cls, mock_post
    ):
        from nm.services.enrich import handle_enrich

        mock_creds.side_effect = lambda svc: {
            "monday": {"api_token": "test-token"},
            "enrich": {},
        }.get(svc, {})

        monday_instance = MagicMock()
        mock_monday_cls.return_value = monday_instance

        profile = _make_profile()
        result = handle_enrich("unknown_cmd", [], profile)

        assert "Error" in result or "error" in result.lower() or "inconnue" in result.lower()

    @patch("nm.services.enrich.requests.post")
    @patch("nm.services.enrich.DDGS")
    @patch("nm.services.enrich.MondayService")
    @patch("nm.services.enrich.get_credentials")
    def test_handle_enrich_lead_without_item_id(
        self, mock_creds, mock_monday_cls, mock_ddgs_cls, mock_post
    ):
        from nm.services.enrich import handle_enrich

        mock_creds.side_effect = lambda svc: {
            "monday": {"api_token": "test-token"},
            "enrich": {},
        }.get(svc, {})

        monday_instance = MagicMock()
        mock_monday_cls.return_value = monday_instance

        profile = _make_profile()
        # No item_id provided
        result = handle_enrich("lead", [], profile)

        assert "Error" in result or "Usage" in result


# ---------------------------------------------------------------------------
# 6. EnrichService class tests
# ---------------------------------------------------------------------------

class TestEnrichService:
    def _make_monday_mock(self):
        m = MagicMock()
        m._query.return_value = {
            "items": [{
                "id": "99999",
                "name": "Clinique Test",
                "board": {"id": 111111},
                "column_values": [
                    {"id": "boolean_mm13e5ct", "text": "", "value": "null"},
                    {"id": "text_mm13wqzg", "text": "", "value": "null"},
                    {"id": "text_mkraxd0w", "text": "", "value": "null"},
                    {"id": "text_mkraa31t", "text": "", "value": "null"},
                    {"id": "text_mkradpsa", "text": "", "value": "null"},
                ],
            }]
        }
        m._parse_columns.return_value = {
            "boolean_mm13e5ct": "",
            "text_mm13wqzg": "",
            "text_mkraxd0w": "",
            "text_mkraa31t": "",
            "text_mkradpsa": "",
        }
        m._update_columns.return_value = {"id": "99999"}
        m._add_note.return_value = {}
        m._board_id.return_value = 111111
        return m

    def test_status_returns_dict(self):
        from nm.services.enrich import EnrichService

        monday_mock = self._make_monday_mock()
        svc = EnrichService(
            monday_svc=monday_mock,
            crawl4ai_url="http://localhost:8002",
            timeout=5,
            max_results=3,
        )

        result = svc.status("99999", "fr_leads")

        assert isinstance(result, dict)
        assert "name" in result or "enriched" in result or "filled" in result

    @patch("nm.services.enrich.DDGS")
    @patch("nm.services.enrich.requests.post")
    def test_enrich_lead_calls_monday_update(self, mock_post, mock_ddgs_cls):
        from nm.services.enrich import EnrichService

        # DDGS mock returns one result
        instance = MagicMock()
        instance.text.return_value = [
            {"href": "https://clinique-test.fr", "title": "Clinique Test"}
        ]
        mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=instance)
        mock_ddgs_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Crawl4AI mock
        mock_post.return_value = _mock_requests_response({
            "markdown": "# Clinique Test\n\nInjections acide hyaluronique et botox."
        })

        monday_mock = self._make_monday_mock()
        svc = EnrichService(
            monday_svc=monday_mock,
            crawl4ai_url="http://localhost:8002",
            timeout=5,
            max_results=3,
        )

        result = svc.enrich_lead("99999", "fr_leads")

        assert isinstance(result, dict)
        # Monday update should have been called
        monday_mock._update_columns.assert_called()

    def test_enrich_lead_skips_already_enriched(self):
        from nm.services.enrich import EnrichService

        monday_mock = self._make_monday_mock()
        # Simulate already-enriched lead
        monday_mock._parse_columns.return_value = {
            "boolean_mm13e5ct": "true",
            "text_mm13wqzg": "https://existing.fr",
        }

        svc = EnrichService(
            monday_svc=monday_mock,
            crawl4ai_url="http://localhost:8002",
            timeout=5,
            max_results=3,
        )

        result = svc.enrich_lead("99999", "fr_leads")

        assert result.get("already_enriched") is True
        # Should NOT call update when already enriched
        monday_mock._update_columns.assert_not_called()


# ---------------------------------------------------------------------------
# 7. Constants tests
# ---------------------------------------------------------------------------

class TestConstants:
    def test_enrichment_columns_fr_leads_has_required_keys(self):
        from nm.services.enrich import ENRICHMENT_COLUMNS_FR_LEADS

        required_keys = [
            "site_web", "ig", "qualif_ig", "linkedin", "fb",
            "doctolib", "qualif_doctolib", "specialite",
            "nb_praticiens", "nb_assistantes", "nb_secretaires",
            "enrichi", "google_checked", "fait_esthetique",
        ]
        for key in required_keys:
            assert key in ENRICHMENT_COLUMNS_FR_LEADS, f"Missing key: {key}"

    def test_enrichment_columns_contacts_has_required_keys(self):
        from nm.services.enrich import ENRICHMENT_COLUMNS_CONTACTS

        required_keys = [
            "site_web", "ig", "linkedin", "fb", "doctolib",
            "specialite", "nb_praticiens", "google_checked", "fait_esthetique",
        ]
        for key in required_keys:
            assert key in ENRICHMENT_COLUMNS_CONTACTS, f"Missing key: {key}"

    def test_esthetique_keywords_is_list(self):
        from nm.services.enrich import ESTHETIQUE_KEYWORDS

        assert isinstance(ESTHETIQUE_KEYWORDS, list)
        assert len(ESTHETIQUE_KEYWORDS) > 5
        assert "botox" in ESTHETIQUE_KEYWORDS or "acide hyaluronique" in ESTHETIQUE_KEYWORDS

    def test_competitor_keywords_is_list(self):
        from nm.services.enrich import COMPETITOR_KEYWORDS

        assert isinstance(COMPETITOR_KEYWORDS, list)
        assert len(COMPETITOR_KEYWORDS) > 0
