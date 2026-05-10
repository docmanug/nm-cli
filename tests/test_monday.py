import json
import pytest
from unittest.mock import patch, MagicMock
from nm.services.monday import MondayService


@pytest.fixture
def monday():
    return MondayService(
        api_token="test-token",
        boards={"fr_leads": 12345, "contacts": 67890, "enrollments": 11111,
                "calls": 22222, "tasks": 33333, "meetings": 44444},
        column_maps={
            "fr_leads": {
                "status": "lead_status", "phone": "lead_phone",
                "email": "lead_email", "company": "lead_company",
                "last_call_date": "date_last",
            },
            "contacts": {
                "status": "nm_lead_status", "phone": "contact_mobile",
                "email": "contact_email", "company": "text_company",
            },
            "enrollments": {
                "statut": "color_statut", "current_step": "numeric_step",
                "step_name": "text_step", "total_attempts": "numeric_attempts",
                "enrolled_date": "date_enrolled", "board_source": "color_source",
                "sdr": "people_sdr", "lead": "rel_lead", "sequence": "rel_seq",
                "source_item_id": "text_source_id", "dernier_canal": "color_canal",
            },
            "calls": {
                "date": "date_call", "heure": "hour_call", "sdr": "people_sdr",
                "duree": "num_duree", "call_type": "color_type",
                "call_outcome": "color_outcome", "linked_contact": "rel_contact",
                "phone": "phone_ext", "transcript_raw": "text_raw",
                "transcript_ia": "text_ia", "note_globale": "text_note",
                "feedback_global": "lt_feedback", "points_ameliorer": "lt_points",
                "pain_level": "color_pain", "digital_maturity": "color_digital",
                "business_mindset": "color_business", "change_friction": "color_friction",
                "lien_call": "text_lien",
            },
            "tasks": {
                "status": "status", "task_type": "color_type",
                "due_date": "date4", "description": "lt_desc",
                "complete_date": "date_complete", "resultat": "color_result",
                "telephone": "phone_tel",
            },
            "meetings": {
                "status": "color_status", "type": "color_type",
                "start_date": "date_start", "end_date": "date_end",
                "duree": "num_duree", "titre": "text_titre",
                "people": "people_who", "contacts_relation": "rel_contacts",
                "attendees": "lt_attendees",
            },
        },
        config={"people_ids": {"sophie": 999, "theo": 888}},
    )


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
                        {"id": "lead_status", "text": "New"},
                        {"id": "lead_phone", "text": "+33612345678"},
                        {"id": "date_last", "text": "2026-05-07"},
                    ],
                }
            ]}}]}
        })
        result = monday.leads_list("fr_leads")
        assert "Dr Dupont" in result
        assert "+33612345678" in result

    @patch("nm.services.monday.requests.post")
    def test_empty_board(self, mock_post, monday):
        mock_post.return_value = _mock_response({
            "data": {"boards": [{"items_page": {"items": []}}]}
        })
        result = monday.leads_list("fr_leads")
        assert "Aucun" in result


class TestLeadsGet:
    @patch("nm.services.monday.requests.post")
    def test_returns_lead_detail(self, mock_post, monday):
        mock_post.return_value = _mock_response({
            "data": {"items": [{
                "id": "111",
                "name": "Dr Dupont",
                "board": {"id": "12345"},
                "column_values": [
                    {"id": "lead_status", "text": "Contacted"},
                    {"id": "lead_phone", "text": "+33612345678"},
                    {"id": "lead_email", "text": "dr@clinic.fr"},
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
        # First call: detect board (get item)
        # Second call: update columns
        mock_post.side_effect = [
            _mock_response({"data": {"items": [{"id": "111", "board": {"id": "12345"},
                            "column_values": [], "updates": []}]}}),
            _mock_response({"data": {"change_multiple_column_values": {"id": "111"}}}),
        ]
        result = monday.leads_update("111", {"status": {"label": "MQL"}})
        assert "111" in result


class TestLeadsNote:
    @patch("nm.services.monday.requests.post")
    def test_add_note(self, mock_post, monday):
        mock_post.return_value = _mock_response({"data": {"create_update": {"id": "999"}}})
        result = monday.leads_note("111", "Prospect chaud")
        assert "111" in result


class TestEnrollmentCreate:
    @patch("nm.services.monday.requests.post")
    def test_creates_enrollment(self, mock_post, monday):
        mock_post.side_effect = [
            _mock_response({"data": {"create_item": {"id": "5555", "name": "Dr Dupont"}}}),
            _mock_response({"data": {"change_multiple_column_values": {"id": "5555"}}}),
        ]
        result = monday.enrollment_create("111", "Dr Dupont", "FR Leads", "99999")
        assert "5555" in result
        assert "Dr Dupont" in result


class TestCallLog:
    @patch("nm.services.monday.requests.post")
    def test_logs_call(self, mock_post, monday):
        mock_post.side_effect = [
            _mock_response({"data": {"create_item": {"id": "7777", "name": "Dr Dupont -- 2026-05-10 14:30"}}}),
            _mock_response({"data": {"change_multiple_column_values": {"id": "7777"}}}),
        ]
        result = monday.call_log("111", "Dr Dupont", {
            "duration": 5,
            "outcome": "RDV pris",
            "call_type": "First attempt",
            "phone": "+33612345678",
        })
        assert "7777" in result


class TestTasksToday:
    @patch("nm.services.monday.requests.post")
    def test_returns_due_tasks(self, mock_post, monday):
        from datetime import date
        today = date.today().isoformat()
        mock_post.return_value = _mock_response({
            "data": {"boards": [{"items_page": {"items": [
                {
                    "id": "8888",
                    "name": "Rappeler Dr Martin",
                    "column_values": [
                        {"id": "status", "text": "To Do"},
                        {"id": "color_type", "text": "Call"},
                        {"id": "date4", "text": today},
                        {"id": "lt_desc", "text": "Rappeler entre 14h et 16h"},
                        {"id": "phone_tel", "text": "+33698765432"},
                    ],
                }
            ]}}]}
        })
        result = monday.tasks_today()
        assert "Rappeler Dr Martin" in result


class TestTasksDone:
    @patch("nm.services.monday.requests.post")
    def test_marks_done(self, mock_post, monday):
        mock_post.return_value = _mock_response({
            "data": {"change_multiple_column_values": {"id": "8888"}}
        })
        result = monday.tasks_done("8888", "RDV")
        assert "8888" in result
        assert "RDV" in result


class TestMeetingCreate:
    @patch("nm.services.monday.requests.post")
    def test_creates_meeting(self, mock_post, monday):
        mock_post.side_effect = [
            _mock_response({"data": {"create_item": {"id": "9999", "name": "Dr Dupont - 15/05 - Demo - 30min"}}}),
            _mock_response({"data": {"change_multiple_column_values": {"id": "9999"}}}),
        ]
        result = monday.meeting_create("111", "Dr Dupont", {
            "date": "2026-05-15",
            "time": "10:00",
            "duration": 30,
            "email": "dr@clinic.fr",
        })
        assert "9999" in result
        assert "Dr Dupont" in result
