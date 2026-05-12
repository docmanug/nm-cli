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
    def check_command(self, svc, cmd): return True
    def get_service_config(self, svc): return {}
    def get_limit(self, svc, cat): return None


@pytest.fixture
def env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("MAILERLITE_API_KEY=test-key\n")
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    return _FakeProfile()


# === SUBSCRIBERS ===

class TestSubscribers:
    @patch("nm.services.mailerlite.requests.get")
    def test_get(self, mock_get):
        mock_get.return_value = _mock_response({"data": {
            "id": "123", "email": "dr@clinic.fr", "name": "", "status": "active",
            "fields": {"name": "Dr Dupont", "last_name": ""},
            "subscribed_at": "2026-01-15", "opened_count": 5, "clicked_count": 2,
            "groups": [{"name": "Challenge"}],
        }})
        assert "dr@clinic.fr" in MailerLiteService("k").subscriber_get("dr@clinic.fr")

    @patch("nm.services.mailerlite.requests.get")
    def test_search(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"email": "a@b.com", "name": "", "status": "active", "fields": {"name": "Alice"}},
        ]})
        assert "a@b.com" in MailerLiteService("k").subscriber_search("test")

    @patch("nm.services.mailerlite.requests.get")
    def test_search_empty(self, mock_get):
        mock_get.return_value = _mock_response({"data": []})
        assert "Aucun" in MailerLiteService("k").subscriber_search("nope")

    @patch("nm.services.mailerlite.requests.get")
    def test_activity(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"type": "open", "created_at": "2026-05-10 10:00", "subject": "Newsletter"},
        ]})
        result = MailerLiteService("k").subscriber_activity("a@b.com")
        assert "open" in result

    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"email": "a@b.com", "name": "", "status": "active", "fields": {"name": "A"}},
        ], "links": {}})
        assert "a@b.com" in MailerLiteService("k").subscribers_list()


# === GROUPS ===

class TestGroups:
    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"id": "g1", "name": "Challenge", "subscribers_count": 13},
        ]})
        result = MailerLiteService("k").groups_list()
        assert "Challenge" in result
        assert "13" in result

    @patch("nm.services.mailerlite.requests.post")
    def test_create(self, mock_post):
        mock_post.return_value = _mock_response({"data": {"id": "g2", "name": "New"}})
        assert "New" in MailerLiteService("k").group_create("New")

    @patch("nm.services.mailerlite.requests.delete")
    def test_delete(self, mock_del):
        mock_del.return_value = _mock_response({}, 204)
        assert "supprime" in MailerLiteService("k").group_delete("g1")


# === CAMPAIGNS ===

class TestCampaigns:
    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [{
            "id": "c1", "name": "Newsletter", "status": "sent",
            "stats": {"sent": 7714, "open_rate": {"string": "51%"}, "click_rate": {"string": "7%"}},
        }]})
        result = MailerLiteService("k").campaigns_list()
        assert "Newsletter" in result
        assert "7714" in result

    @patch("nm.services.mailerlite.requests.get")
    def test_get(self, mock_get):
        mock_get.return_value = _mock_response({"data": {
            "id": "c1", "name": "NL", "status": "sent", "type": "regular",
            "created_at": "2026-01-26", "scheduled_for": "2026-01-26 08:20",
            "stats": {"sent": 100, "deliveries_count": 99, "opens_count": 50,
                       "open_rate": {"string": "50%"}, "clicks_count": 10,
                       "click_rate": {"string": "10%"}, "click_to_open_rate": {"string": "20%"},
                       "unsubscribes_count": 1, "unsubscribe_rate": {"string": "1%"},
                       "hard_bounces_count": 0, "soft_bounces_count": 1},
        }})
        result = MailerLiteService("k").campaign_get("c1")
        assert "50%" in result

    @patch("nm.services.mailerlite.requests.post")
    def test_create(self, mock_post):
        mock_post.return_value = _mock_response({"data": {"id": "c2", "name": "Test", "status": "draft"}})
        result = MailerLiteService("k").campaign_create("Test", "Sujet", "a@b.com", "Dr E")
        assert "creee" in result

    @patch("nm.services.mailerlite.requests.delete")
    def test_delete(self, mock_del):
        mock_del.return_value = _mock_response({}, 204)
        assert "supprimee" in MailerLiteService("k").campaign_delete("c1")

    @patch("nm.services.mailerlite.requests.post")
    def test_cancel(self, mock_post):
        mock_post.return_value = _mock_response({})
        assert "annulee" in MailerLiteService("k").campaign_cancel("c1")

    @patch("nm.services.mailerlite.requests.post")
    def test_schedule(self, mock_post):
        mock_post.return_value = _mock_response({})
        assert "programmee" in MailerLiteService("k").campaign_schedule("c1", "2026-06-01 10:00:00")


# === AUTOMATIONS ===

class TestAutomations:
    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [{
            "id": "a1", "name": "Welcome", "enabled": True, "steps_count": 5,
            "triggers": [{"type": "subscriber_joins_group"}],
        }]})
        result = MailerLiteService("k").automations_list()
        assert "Welcome" in result
        assert "active" in result

    @patch("nm.services.mailerlite.requests.get")
    def test_get(self, mock_get):
        mock_get.return_value = _mock_response({"data": {
            "id": "a1", "name": "Welcome", "enabled": True, "steps_count": 5,
            "created_at": "2026-04-23", "stats": {"completed_count": 10},
        }})
        result = MailerLiteService("k").automation_get("a1")
        assert "Welcome" in result

    @patch("nm.services.mailerlite.requests.delete")
    def test_delete(self, mock_del):
        mock_del.return_value = _mock_response({}, 204)
        assert "supprimee" in MailerLiteService("k").automation_delete("a1")

    @patch("nm.services.mailerlite.requests.get")
    def test_activity(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"subscriber": {"email": "a@b.com"}, "created_at": "2026-05-10"},
        ]})
        result = MailerLiteService("k").automation_activity("a1")
        assert "a@b.com" in result


# === SEGMENTS ===

class TestSegments:
    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [{"id": "s1", "name": "VIP"}]})
        assert "VIP" in MailerLiteService("k").segments_list()

    @patch("nm.services.mailerlite.requests.post")
    def test_create(self, mock_post):
        mock_post.return_value = _mock_response({"data": {"id": "s2", "name": "New seg"}})
        assert "cree" in MailerLiteService("k").segment_create("New seg")

    @patch("nm.services.mailerlite.requests.delete")
    def test_delete(self, mock_del):
        mock_del.return_value = _mock_response({}, 204)
        assert "supprime" in MailerLiteService("k").segment_delete("s1")


# === FORMS ===

class TestForms:
    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"id": "f1", "name": "Popup", "subscribers_count": 5},
        ]})
        assert "Popup" in MailerLiteService("k").forms_list()

    @patch("nm.services.mailerlite.requests.get")
    def test_get(self, mock_get):
        mock_get.return_value = _mock_response({"data": {
            "id": "f1", "name": "Popup", "type": "popup", "subscribers_count": 5, "created_at": "2026-01",
        }})
        result = MailerLiteService("k").form_get("f1")
        assert "Popup" in result

    @patch("nm.services.mailerlite.requests.post")
    def test_create(self, mock_post):
        mock_post.return_value = _mock_response({"data": {"id": "f2", "name": "New"}})
        assert "cree" in MailerLiteService("k").form_create("New", "popup", ["g1"])

    @patch("nm.services.mailerlite.requests.delete")
    def test_delete(self, mock_del):
        mock_del.return_value = _mock_response({}, 204)
        assert "supprime" in MailerLiteService("k").form_delete("f1")


# === FIELDS ===

class TestFields:
    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"key": "name", "name": "Name", "type": "text"},
        ]})
        assert "Name" in MailerLiteService("k").fields_list()

    @patch("nm.services.mailerlite.requests.post")
    def test_create(self, mock_post):
        mock_post.return_value = _mock_response({"data": {"key": "company", "name": "Company"}})
        assert "cree" in MailerLiteService("k").field_create("Company")

    @patch("nm.services.mailerlite.requests.put")
    def test_update(self, mock_put):
        mock_put.return_value = _mock_response({"data": {"name": "Societe"}})
        assert "renomme" in MailerLiteService("k").field_update("123", "Societe")

    @patch("nm.services.mailerlite.requests.delete")
    def test_delete(self, mock_del):
        mock_del.return_value = _mock_response({}, 204)
        assert "supprime" in MailerLiteService("k").field_delete("123")


# === WEBHOOKS ===

class TestWebhooks:
    @patch("nm.services.mailerlite.requests.get")
    def test_list(self, mock_get):
        mock_get.return_value = _mock_response({"data": [
            {"id": "w1", "name": "Hook1", "url": "https://example.com", "events": ["subscriber.created"], "enabled": True},
        ]})
        assert "Hook1" in MailerLiteService("k").webhooks_list()

    @patch("nm.services.mailerlite.requests.post")
    def test_create(self, mock_post):
        mock_post.return_value = _mock_response({"data": {"id": "w2", "url": "https://x.com"}})
        assert "cree" in MailerLiteService("k").webhook_create("https://x.com", ["subscriber.created"])

    @patch("nm.services.mailerlite.requests.delete")
    def test_delete(self, mock_del):
        mock_del.return_value = _mock_response({}, 204)
        assert "supprime" in MailerLiteService("k").webhook_delete("w1")


# === DRY-RUN ===

class TestDryRun:
    def test_subscriber_add(self, env):
        r = handle_mailerlite("subscriber.add", ["a@b.com", "--name", "Test"], env)
        assert "DRY RUN" in r

    @patch("nm.services.mailerlite.requests.post")
    def test_subscriber_add_confirm(self, mock_post, env):
        mock_post.return_value = _mock_response({"data": {"id": "1", "email": "a@b.com"}})
        r = handle_mailerlite("subscriber.add", ["a@b.com", "--confirm"], env)
        assert "ajoute" in r

    def test_subscriber_update(self, env):
        r = handle_mailerlite("subscriber.update", ["a@b.com", "--name", "New"], env)
        assert "DRY RUN" in r

    def test_subscriber_delete(self, env):
        r = handle_mailerlite("subscriber.delete", ["a@b.com"], env)
        assert "DRY RUN" in r

    def test_group_create(self, env):
        r = handle_mailerlite("group.create", ["--name", "Test"], env)
        assert "DRY RUN" in r

    def test_group_delete(self, env):
        r = handle_mailerlite("group.delete", ["g1"], env)
        assert "DRY RUN" in r

    def test_campaign_create(self, env):
        r = handle_mailerlite("campaign.create",
            ["--name", "T", "--subject", "S", "--from", "a@b.com", "--from-name", "N"], env)
        assert "DRY RUN" in r

    def test_campaign_delete(self, env):
        r = handle_mailerlite("campaign.delete", ["c1"], env)
        assert "DRY RUN" in r

    def test_campaign_cancel(self, env):
        r = handle_mailerlite("campaign.cancel", ["c1"], env)
        assert "DRY RUN" in r

    def test_campaign_schedule(self, env):
        r = handle_mailerlite("campaign.schedule", ["c1", "--date", "2026-06-01 10:00:00"], env)
        assert "DRY RUN" in r

    def test_webhook_create(self, env):
        r = handle_mailerlite("webhook.create", ["--url", "https://x.com", "--events", "subscriber.created"], env)
        assert "DRY RUN" in r

    def test_field_create(self, env):
        r = handle_mailerlite("field.create", ["--name", "Company"], env)
        assert "DRY RUN" in r

    def test_segment_create(self, env):
        r = handle_mailerlite("segment.create", ["--name", "VIP"], env)
        assert "DRY RUN" in r

    def test_import(self, env):
        r = handle_mailerlite("subscribers.import", ["--group", "g1", "--emails", "a@b.com,c@d.com"], env)
        assert "DRY RUN" in r
        assert "2" in r  # 2 subscribers
