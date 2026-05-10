import json
import pytest
from unittest.mock import patch, MagicMock
from nm.services.monday import MondayService


@pytest.fixture
def monday():
    return MondayService(api_token="test-token", board_id=12345)


def _mock_response(data):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


class TestLeadsList:
    @patch("nm.services.monday.requests.post")
    def test_returns_formatted_leads(self, mock_post, monday):
        mock_post.return_value = _mock_response({
            "data": {"boards": [{"items_page": {"items": [
                {
                    "id": "111",
                    "name": "Dr Dupont",
                    "column_values": [
                        {"id": "status", "text": "New"},
                        {"id": "phone", "text": "+33612345678"},
                        {"id": "date", "text": "2026-05-07"},
                    ],
                }
            ]}}]}
        })
        result = monday.leads_list()
        assert "Dr Dupont" in result
        assert "+33612345678" in result

    @patch("nm.services.monday.requests.post")
    def test_empty_board(self, mock_post, monday):
        mock_post.return_value = _mock_response({
            "data": {"boards": [{"items_page": {"items": []}}]}
        })
        result = monday.leads_list()
        assert "Aucun" in result


class TestLeadsGet:
    @patch("nm.services.monday.requests.post")
    def test_returns_lead_detail(self, mock_post, monday):
        mock_post.return_value = _mock_response({
            "data": {"items": [{
                "id": "111",
                "name": "Dr Dupont",
                "column_values": [
                    {"id": "status", "text": "Contacted"},
                    {"id": "phone", "text": "+33612345678"},
                    {"id": "email", "text": "dr@clinic.fr"},
                ],
                "updates": [{"text_body": "Appel OK", "created_at": "2026-05-10"}],
            }]}
        })
        result = monday.leads_get("111")
        assert "Dr Dupont" in result
        assert "Contacted" in result


class TestLeadsUpdate:
    @patch("nm.services.monday.requests.post")
    def test_update_status(self, mock_post, monday):
        mock_post.return_value = _mock_response({"data": {"change_column_value": {"id": "111"}}})
        result = monday.leads_update("111", status="Demo booked")
        assert "111" in result
        assert "Demo booked" in result


class TestLeadsNote:
    @patch("nm.services.monday.requests.post")
    def test_add_note(self, mock_post, monday):
        mock_post.return_value = _mock_response({"data": {"create_update": {"id": "999"}}})
        result = monday.leads_note("111", "Prospect chaud")
        assert "111" in result
