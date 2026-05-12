from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from nm.services.unipile import UnipileService, handle_unipile, _resolve_post_id


# --- extract_post_id ---


class TestExtractPostId:
    def test_activity_url(self):
        url = "https://www.linkedin.com/feed/update/activity-7459882606189309952"
        assert UnipileService.extract_post_id(url) == "7459882606189309952"

    def test_ugcpost_url(self):
        url = "https://www.linkedin.com/feed/update/urn:li:ugcPost:7459882606189309952"
        assert UnipileService.extract_post_id(url) == "urn:li:ugcPost:7459882606189309952"

    def test_share_url(self):
        url = "https://www.linkedin.com/feed/update/urn:li:share:1234567890"
        assert UnipileService.extract_post_id(url) == "urn:li:share:1234567890"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            UnipileService.extract_post_id("https://linkedin.com/in/someone")


# --- _parse_author ---


class TestParseAuthor:
    def test_author_as_dict(self):
        name, headline = UnipileService._parse_author({"name": "Dr Dupont", "headline": "Medecin"})
        assert name == "Dr Dupont"
        assert headline == "Medecin"

    def test_author_as_string(self):
        name, headline = UnipileService._parse_author("Dr Dupont")
        assert name == "Dr Dupont"
        assert headline == ""

    def test_author_as_none(self):
        name, headline = UnipileService._parse_author(None)
        assert name == "?"

    def test_author_dict_no_name(self):
        name, headline = UnipileService._parse_author({"headline": "Medecin"})
        assert name == "?"
        assert headline == "Medecin"


# --- _resolve_post_id helper ---


class TestResolvePostId:
    def test_plain_id_passthrough(self):
        assert _resolve_post_id("12345") == "12345"

    def test_linkedin_url_extracted(self):
        url = "https://linkedin.com/feed/update/urn:li:ugcPost:999"
        assert _resolve_post_id(url) == "urn:li:ugcPost:999"


# --- Dry-run / --confirm ---


def _mock_response(data, status=200):
    mock = MagicMock()
    mock.status_code = status
    mock.ok = status < 400
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
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
    env_file.write_text("UNIPILE_API_KEY=test-key\n")
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    monkeypatch.setenv("UNIPILE_BASE_URL", "https://test.example.com:15390")
    return _FakeProfile()


class TestDryRun:
    @patch("nm.services.unipile.requests.get")
    def test_comment_without_confirm_shows_dry_run(self, mock_get, env):
        # Mock the accounts list for _resolve_account_id
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        result = handle_unipile(
            "post.comment",
            ["post123", "--text", "Hello world"],
            env,
        )
        assert "DRY RUN" in result
        assert "post123" in result
        assert "Hello world" in result
        assert "--confirm" in result

    @patch("nm.services.unipile.requests.post")
    @patch("nm.services.unipile.requests.get")
    def test_comment_with_confirm_posts(self, mock_get, mock_post, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        mock_post.return_value = _mock_response({"id": "comment_456"})
        result = handle_unipile(
            "post.comment",
            ["post123", "--text", "Hello world", "--confirm"],
            env,
        )
        assert "Commentaire publie" in result
        assert "comment_456" in result
        mock_post.assert_called_once()

    @patch("nm.services.unipile.requests.get")
    def test_reply_without_confirm_shows_dry_run(self, mock_get, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        result = handle_unipile(
            "comment.reply",
            ["cmt789", "--post-id", "post123", "--text", "Merci"],
            env,
        )
        assert "DRY RUN" in result
        assert "cmt789" in result
        assert "Merci" in result

    @patch("nm.services.unipile.requests.post")
    @patch("nm.services.unipile.requests.get")
    def test_reply_with_confirm_posts(self, mock_get, mock_post, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        mock_post.return_value = _mock_response({"id": "reply_001"})
        result = handle_unipile(
            "comment.reply",
            ["cmt789", "--post-id", "post123", "--text", "Merci", "--confirm"],
            env,
        )
        assert "Reponse publiee" in result
        assert "reply_001" in result


# --- Explicit --account-id ---


class TestAccountId:
    @patch("nm.services.unipile.requests.get")
    def test_explicit_account_id_used(self, mock_get, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        result = handle_unipile(
            "post.comment",
            ["post123", "--text", "test", "--account-id", "GpP9p7JuTlu5Zz14DafeHw"],
            env,
        )
        assert "DRY RUN" in result
        assert "GpP9p7JuTlu5Zz14DafeHw" in result

    @patch("nm.services.unipile.requests.post")
    @patch("nm.services.unipile.requests.get")
    def test_explicit_account_id_in_post_payload(self, mock_get, mock_post, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        mock_post.return_value = _mock_response({"id": "c1"})
        handle_unipile(
            "post.comment",
            ["post123", "--text", "yo", "--account-id", "CUSTOM_ID", "--confirm"],
            env,
        )
        call_args = mock_post.call_args
        payload = call_args[1].get("json") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("json")
        assert payload["account_id"] == "CUSTOM_ID"


# --- React not available ---


class TestReact:
    @patch("nm.services.unipile.requests.get")
    def test_react_dry_run(self, mock_get, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        result = handle_unipile("post.react", ["post123"], env)
        assert "DRY RUN" in result
        assert "post123" in result
        assert "like" in result

    @patch("nm.services.unipile.requests.post")
    @patch("nm.services.unipile.requests.get")
    def test_react_with_confirm(self, mock_get, mock_post, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        mock_post.return_value = _mock_response({"object": "ReactionAdded"})
        result = handle_unipile("post.react", ["post123", "--confirm"], env)
        assert "Reaction ajoutee" in result
        assert "ReactionAdded" in result

    @patch("nm.services.unipile.requests.post")
    @patch("nm.services.unipile.requests.get")
    def test_react_custom_type(self, mock_get, mock_post, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        mock_post.return_value = _mock_response({"object": "ReactionAdded"})
        result = handle_unipile("post.react", ["post123", "--type", "celebrate", "--confirm"], env)
        assert "Reaction ajoutee" in result
        call_payload = mock_post.call_args[1].get("json")
        assert call_payload["reaction_type"] == "celebrate"

    def test_unreact_not_available(self, env):
        result = handle_unipile("post.unreact", ["post123"], env)
        assert "Error" in result
        assert "non disponible" in result.lower()

    @patch("nm.services.unipile.requests.get")
    def test_comment_react_dry_run(self, mock_get, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        result = handle_unipile(
            "comment.react",
            ["cmt123", "--post-id", "post456"],
            env,
        )
        assert "DRY RUN" in result
        assert "cmt123" in result

    @patch("nm.services.unipile.requests.post")
    @patch("nm.services.unipile.requests.get")
    def test_comment_react_with_confirm(self, mock_get, mock_post, env):
        mock_get.return_value = _mock_response({
            "items": [{"id": "acc123", "type": "LINKEDIN"}]
        })
        mock_post.return_value = _mock_response({"object": "ReactionAdded"})
        result = handle_unipile(
            "comment.react",
            ["cmt123", "--post-id", "post456", "--confirm"],
            env,
        )
        assert "Reaction ajoutee sur commentaire" in result


# --- Comment payload ---


class TestCommentPayload:
    @patch("nm.services.unipile.requests.post")
    def test_post_comment_payload_shape(self, mock_post):
        mock_post.return_value = _mock_response({"id": "c1"})
        svc = UnipileService(api_key="k", base_url="https://test.example.com")
        svc.post_comment("post123", "Hello", account_id="acc1")
        call_args = mock_post.call_args
        payload = call_args[1].get("json") or call_args[0][1]
        assert payload == {"account_id": "acc1", "text": "Hello"}
        assert "/api/v1/posts/post123/comments" in call_args[1].get("url", call_args[0][0])

    @patch("nm.services.unipile.requests.post")
    def test_comment_reply_payload_has_comment_id(self, mock_post):
        mock_post.return_value = _mock_response({"id": "r1"})
        svc = UnipileService(api_key="k", base_url="https://test.example.com")
        svc.comment_reply("post123", "cmt456", "Merci", account_id="acc1")
        call_args = mock_post.call_args
        payload = call_args[1].get("json") or call_args[0][1]
        assert payload["comment_id"] == "cmt456"
        assert payload["text"] == "Merci"
        assert payload["account_id"] == "acc1"


# --- Missing --text ---


class TestMissingArgs:
    def test_comment_missing_text(self, env):
        result = handle_unipile("post.comment", ["post123"], env)
        assert "Error" in result
        assert "--text" in result

    def test_reply_missing_post_id(self, env):
        result = handle_unipile("comment.reply", ["cmt1", "--text", "hi"], env)
        assert "Error" in result
