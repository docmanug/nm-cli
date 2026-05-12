from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from nm.services.mailerlite import MailerLiteService, handle_mailerlite


def _mock_response(data, status=200):
    mock = MagicMock()
    mock.ok = status < 400
    mock.status_code = status
    mock.json.return_value = data
    mock.text = ""
    return mock


class _FakeProfile:
    name = "test"
    def check_command(self, svc, cmd):
        return True
    def get_service_config(self, svc):
        return {}
    def get_limit(self, svc, cat):
        return None


@pytest.fixture
def env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("MAILERLITE_API_KEY=test-key\n")
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    return _FakeProfile()


# --- Subscriber ---


class TestSubscriberGet:
    @patch("nm.services.mailerlite.requests.get")
    def test_returns_subscriber(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": {
                "id": "123",
                "email": "dr@clinic.fr",
                "name": "Dr Dupont",
                "status": "active",
                "fields": {"name": "Dr Dupont", "last_name": ""},
                "subscribed_at": "2026-01-15 10:00:00",
                "opened_count": 5,
                "clicked_count": 2,
                "groups": [{"name": "Challenge 5 Jours IA"}],
            }
        })
        svc = MailerLiteService(api_key="k")
        result = svc.subscriber_get("dr@clinic.fr")
        assert "dr@clinic.fr" in result
        assert "Dr Dupont" in result
        assert "active" in result
        assert "Challenge" in result


class TestSubscriberSearch:
    @patch("nm.services.mailerlite.requests.get")
    def test_search_results(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [
                {"email": "a@b.com", "name": "", "status": "active", "fields": {"name": "Alice"}},
                {"email": "c@d.com", "name": "", "status": "active", "fields": {"name": "Charlie"}},
            ]
        })
        svc = MailerLiteService(api_key="k")
        result = svc.subscriber_search("test")
        assert "2 abonnes" in result
        assert "a@b.com" in result

    @patch("nm.services.mailerlite.requests.get")
    def test_search_empty(self, mock_get):
        mock_get.return_value = _mock_response({"data": []})
        svc = MailerLiteService(api_key="k")
        result = svc.subscriber_search("nonexistent")
        assert "Aucun" in result


# --- Groups ---


class TestGroupsList:
    @patch("nm.services.mailerlite.requests.get")
    def test_returns_groups(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [
                {"id": "g1", "name": "Challenge", "subscribers_count": 13},
                {"id": "g2", "name": "Import", "subscribers_count": 0},
            ]
        })
        svc = MailerLiteService(api_key="k")
        result = svc.groups_list()
        assert "2 groupes" in result
        assert "Challenge" in result
        assert "13 abonnes" in result


# --- Campaigns ---


class TestCampaignsList:
    @patch("nm.services.mailerlite.requests.get")
    def test_returns_campaigns(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [{
                "id": "c1",
                "name": "Newsletter janvier",
                "status": "sent",
                "stats": {
                    "sent": 7714,
                    "open_rate": {"string": "51.45%"},
                    "click_rate": {"string": "7.7%"},
                },
            }]
        })
        svc = MailerLiteService(api_key="k")
        result = svc.campaigns_list()
        assert "Newsletter janvier" in result
        assert "7714" in result
        assert "51.45%" in result


class TestCampaignGet:
    @patch("nm.services.mailerlite.requests.get")
    def test_returns_detail(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": {
                "id": "c1",
                "name": "Newsletter",
                "status": "sent",
                "type": "regular",
                "created_at": "2026-01-26 08:03:09",
                "scheduled_for": "2026-01-26 08:20:03",
                "stats": {
                    "sent": 7714,
                    "deliveries_count": 7710,
                    "opens_count": 3969,
                    "open_rate": {"string": "51.45%"},
                    "clicks_count": 594,
                    "click_rate": {"string": "7.7%"},
                    "click_to_open_rate": {"string": "14.97%"},
                    "unsubscribes_count": 93,
                    "unsubscribe_rate": {"string": "1.21%"},
                    "hard_bounces_count": 4,
                    "soft_bounces_count": 233,
                },
                "dashboard_url": "https://dashboard.mailerlite.com/campaigns/c1",
            }
        })
        svc = MailerLiteService(api_key="k")
        result = svc.campaign_get("c1")
        assert "Newsletter" in result
        assert "51.45%" in result
        assert "7714" in result
        assert "dashboard.mailerlite.com" in result


# --- Automations ---


class TestAutomationsList:
    @patch("nm.services.mailerlite.requests.get")
    def test_returns_automations(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [{
                "id": "a1",
                "name": "Welcome",
                "enabled": True,
                "steps_count": 5,
                "triggers": [{"type": "subscriber_joins_group"}],
            }]
        })
        svc = MailerLiteService(api_key="k")
        result = svc.automations_list()
        assert "Welcome" in result
        assert "active" in result


# --- Dry-run subscriber add ---


class TestDryRun:
    def test_subscriber_add_dry_run(self, env):
        result = handle_mailerlite(
            "subscriber.add",
            ["test@example.com", "--name", "Dr Test"],
            env,
        )
        assert "DRY RUN" in result
        assert "test@example.com" in result
        assert "Dr Test" in result

    @patch("nm.services.mailerlite.requests.post")
    def test_subscriber_add_with_confirm(self, mock_post, env):
        mock_post.return_value = _mock_response({
            "data": {"id": "123", "email": "test@example.com"}
        })
        result = handle_mailerlite(
            "subscriber.add",
            ["test@example.com", "--name", "Dr Test", "--confirm"],
            env,
        )
        assert "Abonne ajoute" in result
        assert "test@example.com" in result

    def test_group_add_subscriber_dry_run(self, env):
        result = handle_mailerlite(
            "group.add-subscriber",
            ["g1", "--subscriber", "test@example.com"],
            env,
        )
        assert "DRY RUN" in result
        assert "g1" in result
        assert "test@example.com" in result


# --- Fields ---


class TestFieldsList:
    @patch("nm.services.mailerlite.requests.get")
    def test_returns_fields(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [
                {"key": "name", "name": "Name", "type": "text"},
                {"key": "company", "name": "Company", "type": "text"},
            ]
        })
        svc = MailerLiteService(api_key="k")
        result = svc.fields_list()
        assert "2 champs" in result
        assert "Name" in result
