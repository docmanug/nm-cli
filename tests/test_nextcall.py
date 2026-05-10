import pytest
from unittest.mock import patch, MagicMock
from nm.services.nextcall import NextCallService


@pytest.fixture
def nextcall():
    return NextCallService(
        api_key="test-key",
        api_url="https://example.com/api/mcp",
        user_id="user1",
    )


def _mock_response(data):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


class TestContactGet:
    @patch("nm.services.nextcall.requests.post")
    def test_returns_contact(self, mock_post, nextcall):
        mock_post.return_value = _mock_response({
            "result": {
                "name": "Dr Dupont",
                "phone": "+33612345678",
                "email": "dr@clinic.fr",
                "company": "Clinique Dupont",
            }
        })
        result = nextcall.contact_get("+33612345678")
        assert "Dr Dupont" in result
        assert "+33612345678" in result


class TestSendWhatsApp:
    @patch("nm.services.nextcall.requests.post")
    def test_send_ok(self, mock_post, nextcall):
        mock_post.return_value = _mock_response({"result": {"status": "sent"}})
        result = nextcall.send_whatsapp("+33612345678", "Bonjour")
        assert "envoye" in result.lower() or "sent" in result.lower()

    def test_message_too_long(self, nextcall):
        result = nextcall.send_whatsapp("+33612345678", "x" * 501, max_length=500)
        assert "Error" in result


class TestSendSMS:
    @patch("nm.services.nextcall.requests.post")
    def test_send_ok(self, mock_post, nextcall):
        mock_post.return_value = _mock_response({"result": {"status": "sent"}})
        result = nextcall.send_sms("+33612345678", "Test SMS")
        assert "envoye" in result.lower() or "sent" in result.lower()


class TestCalendarCheck:
    @patch("nm.services.nextcall.requests.post")
    def test_returns_slots(self, mock_post, nextcall):
        mock_post.return_value = _mock_response({
            "result": {
                "busy": [
                    {"start": "2026-05-13T09:00:00", "end": "2026-05-13T10:00:00"},
                ]
            }
        })
        result = nextcall.calendar_check("2026-05-13")
        assert "2026-05-13" in result


class TestCalendarBook:
    @patch("nm.services.nextcall.requests.post")
    def test_book_ok(self, mock_post, nextcall):
        mock_post.return_value = _mock_response({
            "result": {"id": "evt_123", "status": "confirmed"}
        })
        result = nextcall.calendar_book("2026-05-13", "10:00", "Demo Nextmotion - Dr X")
        assert "confirme" in result.lower() or "confirmed" in result.lower()
