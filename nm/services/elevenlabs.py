from __future__ import annotations
import requests
from nm.core.output import format_call_result, format_calls_list, format_error

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


class ElevenLabsService:
    def __init__(self, api_key: str, agent_id: str, phone_number_id: str = ""):
        self._api_key = api_key
        self._agent_id = agent_id
        self._phone_number_id = phone_number_id
        self._headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }

    def call_trigger(self, phone: str, context: str = "",
                     prospect_name: str = "", lead_id: str = "",
                     contact_id: str = "", call_type: str = "First attempt",
                     hook_type: str = "cold_intro") -> str:
        if not self._phone_number_id:
            return format_error("ELEVENLABS_PHONE_NUMBER_ID non configure")
        dyn_vars = {
            "prospect_name": prospect_name or "Inconnu",
            "call_type": call_type,
            "hook_type": hook_type,
        }
        if context:
            dyn_vars["context"] = context
        if lead_id:
            dyn_vars["lead_item_id"] = lead_id
        if contact_id:
            dyn_vars["contact_item_id"] = contact_id
        resp = requests.post(
            f"{ELEVENLABS_API_URL}/convai/twilio/outbound-call",
            headers=self._headers,
            json={
                "agent_id": self._agent_id,
                "agent_phone_number_id": self._phone_number_id,
                "to_number": phone,
                "conversation_initiation_client_data": {
                    "dynamic_variables": dyn_vars
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        conv_id = data.get("conversation_id", "?")
        return f"Appel lance — conversation: {conv_id}"

    def call_result(self, conversation_id: str) -> str:
        resp = requests.get(
            f"{ELEVENLABS_API_URL}/convai/conversations/{conversation_id}",
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()
        analysis = data.get("analysis", {})
        result = {
            "id": conversation_id,
            "contact": data.get("metadata", {}).get("to_number", "?"),
            "duration": f"{data.get('call_duration_secs', 0)}s",
            "result": "Reussi" if analysis.get("call_successful") == "true" else "Echec",
            "summary": analysis.get("transcript_summary", "Pas de resume"),
        }
        return format_call_result(result)

    def call_list_today(self) -> str:
        resp = requests.get(
            f"{ELEVENLABS_API_URL}/convai/conversations",
            headers=self._headers,
            params={"agent_id": self._agent_id},
        )
        resp.raise_for_status()
        data = resp.json()
        conversations = data.get("conversations", [])
        calls = []
        for conv in conversations:
            calls.append({
                "id": conv.get("conversation_id", "?"),
                "contact": conv.get("metadata", {}).get("to_number", "?"),
                "result": conv.get("status", "?"),
                "duration": f"{conv.get('call_duration_secs', 0)}s",
            })
        return format_calls_list(calls)


def handle_elevenlabs(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials
    from nm.core.limits import LimitTracker

    creds = get_credentials("elevenlabs")
    svc = ElevenLabsService(
        api_key=creds["api_key"],
        agent_id=creds["agent_id"],
        phone_number_id=creds.get("phone_number_id", ""),
    )
    tracker = LimitTracker()

    if command == "call.trigger":
        limit = profile.get_limit("elevenlabs", "calls")
        if not tracker.check_and_increment("calls", limit):
            from nm.core.output import format_limit_hit
            return format_limit_hit("calls", tracker.get_count("calls"), limit)
        if not args:
            return format_error('Usage: nm elevenlabs call trigger <phone> [--name "Dr X"] [--lead-id 123] [--context "..."]')
        phone = args[0]
        # Parse flags
        def _flag(name):
            for i, a in enumerate(args):
                if a == f"--{name}" and i + 1 < len(args):
                    return args[i + 1]
            return ""
        return svc.call_trigger(
            phone,
            context=_flag("context"),
            prospect_name=_flag("name"),
            lead_id=_flag("lead-id"),
            contact_id=_flag("contact-id"),
            call_type=_flag("call-type") or "First attempt",
            hook_type=_flag("hook-type") or "cold_intro",
        )
    elif command == "call.result":
        if not args:
            return format_error("Usage: nm elevenlabs call result <conversation_id>")
        return svc.call_result(args[0])
    elif command == "call.list-today":
        return svc.call_list_today()
    else:
        return format_error(f"Commande ElevenLabs inconnue: {command}")
