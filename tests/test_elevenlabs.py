from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from nm.services.elevenlabs import ElevenLabsService


@pytest.fixture
def elevenlabs():
    return ElevenLabsService(api_key="test-key", agent_id="agent_123", phone_number_id="phnum_test")


def _mock_response(data, status=200):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


class TestCallTrigger:
    @patch("nm.services.elevenlabs.requests.post")
    def test_trigger_ok(self, mock_post, elevenlabs):
        mock_post.return_value = _mock_response({
            "conversation_id": "conv_abc123",
        })
        result = elevenlabs.call_trigger("+33612345678", "Lead chaud, demo demain")
        assert "conv_abc123" in result


class TestCallResult:
    @patch("nm.services.elevenlabs.requests.get")
    def test_result_ok(self, mock_get, elevenlabs):
        mock_get.return_value = _mock_response({
            "conversation_id": "conv_abc123",
            "status": "done",
            "analysis": {
                "call_successful": "true",
                "transcript_summary": "Le prospect est interesse",
            },
        })
        result = elevenlabs.call_result("conv_abc123")
        assert "interesse" in result.lower()


class TestCallListToday:
    @patch("nm.services.elevenlabs.requests.get")
    def test_list_today(self, mock_get, elevenlabs):
        mock_get.return_value = _mock_response({
            "conversations": [
                {"conversation_id": "c1", "status": "done", "call_duration_secs": 120},
                {"conversation_id": "c2", "status": "done", "call_duration_secs": 90},
            ]
        })
        result = elevenlabs.call_list_today()
        assert "2" in result
