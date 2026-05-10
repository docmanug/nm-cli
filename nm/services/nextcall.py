from __future__ import annotations
import requests
from nm.core.output import (
    format_contact,
    format_send_confirmation,
    format_error,
    format_nextcall_calls_list,
    format_nextcall_call_detail,
    format_nextcall_call_stats,
    format_meeting_transcript,
    format_meeting_transcripts_list,
)


class NextCallService:
    def __init__(self, api_key: str, api_url: str, user_id: str):
        self._api_key = api_key
        self._api_url = api_url
        self._user_id = user_id

    def _call_tool(self, tool: str, params: dict = None) -> dict:
        payload = {
            "method": "tools/call",
            "params": {"name": tool, "arguments": params or {}},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(self._api_url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", data)

    def contact_get(self, query: str) -> str:
        result = self._call_tool("contacts_search", {"query": query})
        if isinstance(result, list):
            contacts = result
        elif isinstance(result, dict):
            contacts = result.get("contacts", [result])
        else:
            return format_error("Format de reponse inattendu")
        if not contacts:
            return format_error(f"Aucun contact trouve pour '{query}'")
        contact = contacts[0] if isinstance(contacts, list) else contacts
        return format_contact(contact)

    def contact_history(self, query: str) -> str:
        result = self._call_tool("contacts_search", {"query": query})
        if isinstance(result, list) and result:
            contact = result[0]
        elif isinstance(result, dict):
            contact = result
        else:
            return format_error(f"Aucun contact trouve pour '{query}'")
        contact_id = contact.get("id")
        if not contact_id:
            return format_error("Contact sans ID")
        detail = self._call_tool("contacts_get", {"contactId": contact_id, "includeHistory": True})
        return format_contact(detail)

    def send_whatsapp(self, phone: str, message: str, max_length: int = None) -> str:
        if max_length and len(message) > max_length:
            return format_error(f"Message trop long ({len(message)} > {max_length} caracteres)")
        result = self._call_tool("whatsapp_send", {
            "userId": self._user_id, "contactId": phone, "body": message,
        })
        return format_send_confirmation("WhatsApp", phone, result.get("status", "envoye"))

    def send_sms(self, phone: str, message: str, max_length: int = None) -> str:
        if max_length and len(message) > max_length:
            return format_error(f"Message trop long ({len(message)} > {max_length} caracteres)")
        result = self._call_tool("sms_send", {
            "userId": self._user_id, "contactId": phone, "body": message,
        })
        return format_send_confirmation("SMS", phone, result.get("status", "envoye"))

    def send_email(self, email: str, subject: str, body: str) -> str:
        result = self._call_tool("gmail_send", {
            "userId": self._user_id, "to": email, "subject": subject, "body": body,
        })
        return format_send_confirmation("Email", email, result.get("status", "envoye"))

    # --- CALLS (read-only) ---

    def calls_list(self, user_id: str | None = None,
                   date_from: str | None = None,
                   date_to: str | None = None,
                   days: int | None = None) -> str:
        params = {}
        if user_id:
            params["userId"] = user_id
        if days and not date_from:
            from datetime import date, timedelta
            date_from = (date.today() - timedelta(days=days)).isoformat()
            date_to = date.today().isoformat()
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        result = self._call_tool("calls_list", params)
        calls_data = result if isinstance(result, list) else result.get("calls", [])
        calls = []
        for c in calls_data:
            contact_name = c.get("contactName", c.get("contact", {}).get("name", "?"))
            calls.append({
                "id": c.get("id", "?"),
                "date": c.get("date", c.get("startedAt", "?"))[:10] if c.get("date", c.get("startedAt")) else "?",
                "contact": contact_name,
                "status": c.get("status", "?"),
                "label": c.get("label", ""),
                "duration": c.get("duration", 0),
                "direction": c.get("direction", "?"),
            })
        period = f"({days} derniers jours)" if days else ""
        return format_nextcall_calls_list(calls, period)

    def calls_get(self, call_id: str, include_coaching: bool = False) -> str:
        params = {"callId": call_id}
        if include_coaching:
            params["includeCoachingTips"] = True
        result = self._call_tool("calls_get", params)
        call = result if isinstance(result, dict) else {}
        contact_name = call.get("contactName", call.get("contact", {}).get("name", "?"))
        return format_nextcall_call_detail({
            "id": call.get("id", call_id),
            "contact": contact_name,
            "date": (call.get("date", call.get("startedAt", "?"))[:10]
                     if call.get("date", call.get("startedAt")) else "?"),
            "status": call.get("status", "?"),
            "label": call.get("label", ""),
            "duration": call.get("duration", 0),
            "direction": call.get("direction", "?"),
            "transcript": call.get("transcript", ""),
            "summary": call.get("summary", call.get("aiSummary", "")),
            "coaching_tips": call.get("coachingTips", []),
        })

    def calls_stats(self, user_id: str | None = None,
                    date_from: str | None = None,
                    date_to: str | None = None,
                    days: int | None = None) -> str:
        params = {}
        if user_id:
            params["userId"] = user_id
        if days and not date_from:
            from datetime import date, timedelta
            date_from = (date.today() - timedelta(days=days)).isoformat()
            date_to = date.today().isoformat()
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        result = self._call_tool("calls_stats", params)
        return format_nextcall_call_stats(result if isinstance(result, dict) else {})

    # --- MEETING TRANSCRIPTS (read-only) ---

    def meeting_transcripts_list(self, user_id: str | None = None,
                                 date_from: str | None = None,
                                 date_to: str | None = None,
                                 days: int | None = None) -> str:
        params = {}
        if user_id:
            params["userId"] = user_id
        if days and not date_from:
            from datetime import date, timedelta
            date_from = (date.today() - timedelta(days=days)).isoformat()
            date_to = date.today().isoformat()
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        result = self._call_tool("meeting_transcripts_list", params)
        transcripts = result if isinstance(result, list) else result.get("transcripts", [])
        items = []
        for t in transcripts:
            items.append({
                "id": t.get("id", "?"),
                "title": t.get("title", "?"),
                "date": t.get("date", t.get("createdAt", "?"))[:10] if t.get("date", t.get("createdAt")) else "?",
                "status": t.get("status", "?"),
                "duration": t.get("duration", "?"),
            })
        return format_meeting_transcripts_list(items)

    def meeting_transcripts_get(self, transcript_id: str) -> str:
        result = self._call_tool("meeting_transcripts_get", {"id": transcript_id})
        t = result if isinstance(result, dict) else {}
        return format_meeting_transcript({
            "id": t.get("id", transcript_id),
            "title": t.get("title", "?"),
            "date": t.get("date", t.get("createdAt", "?"))[:10] if t.get("date", t.get("createdAt")) else "?",
            "participants": t.get("participants", []),
            "status": t.get("status", "?"),
            "summary": t.get("summary", t.get("aiSummary", "")),
            "transcript": t.get("transcript", t.get("text", "")),
        })

    def meeting_transcripts_recent(self, contact_id: str | None = None,
                                    contact_email: str | None = None,
                                    user_id: str | None = None) -> str:
        params = {}
        if contact_id:
            params["contactId"] = contact_id
        if contact_email:
            params["contactEmail"] = contact_email
        if user_id:
            params["userId"] = user_id
        result = self._call_tool("meeting_transcripts_recent", params)
        transcripts = result if isinstance(result, list) else result.get("transcripts", [])
        items = []
        for t in transcripts:
            items.append({
                "id": t.get("id", "?"),
                "title": t.get("title", "?"),
                "date": t.get("date", t.get("createdAt", "?"))[:10] if t.get("date", t.get("createdAt")) else "?",
                "status": t.get("status", "?"),
                "duration": t.get("duration", "?"),
            })
        return format_meeting_transcripts_list(items)

    def calendar_check(self, date_str: str) -> str:
        result = self._call_tool("calendar_freebusy", {
            "userId": self._user_id,
            "timeMin": f"{date_str}T08:00:00",
            "timeMax": f"{date_str}T19:00:00",
        })
        busy = result.get("busy", [])
        lines = [f"Disponibilites {date_str}:\n"]
        if not busy:
            lines.append("  Journee entierement libre (9h-18h)")
        else:
            lines.append("  Creneaux occupes:")
            for slot in busy:
                start = slot.get("start", "?").split("T")[1][:5] if "T" in slot.get("start", "") else "?"
                end = slot.get("end", "?").split("T")[1][:5] if "T" in slot.get("end", "") else "?"
                lines.append(f"    {start} - {end}")
        return "\n".join(lines)

    def calendar_book(self, date_str: str, time: str, title: str) -> str:
        start = f"{date_str}T{time}:00"
        hour, minute = time.split(":")
        end_hour = int(hour)
        end_minute = int(minute) + 30
        if end_minute >= 60:
            end_hour += 1
            end_minute -= 60
        end = f"{date_str}T{end_hour:02d}:{end_minute:02d}:00"
        result = self._call_tool("calendar_create_event", {
            "userId": self._user_id,
            "summary": title,
            "startDateTime": start,
            "endDateTime": end,
        })
        event_id = result.get("id", "?")
        return f"Demo confirmee : {title} le {date_str} a {time} (event: {event_id})"


def handle_nextcall(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials
    from nm.core.limits import LimitTracker

    creds = get_credentials("nextcall")
    config = profile.get_service_config("nextcall") or {}
    max_msg_len = config.get("max_message_length")

    svc = NextCallService(api_key=creds["api_key"], api_url=creds["api_url"], user_id=creds["user_id"])
    tracker = LimitTracker()

    def get_flag(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == f"--{flag}" and i + 1 < len(args):
                return args[i + 1]
        return None

    if command == "contact.get":
        if not args:
            return format_error("Usage: nm nextcall contact get <phone_or_email>")
        return svc.contact_get(args[0])
    elif command == "contact.history":
        if not args:
            return format_error("Usage: nm nextcall contact history <phone_or_email>")
        return svc.contact_history(args[0])

    # --- CALLS (read-only) ---
    elif command == "calls.list":
        user_id = get_flag("user") or creds.get("user_id")
        date_from = get_flag("from")
        date_to = get_flag("to")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.calls_list(user_id, date_from, date_to, days)

    elif command == "calls.get":
        if not args:
            return format_error("Usage: nm nextcall calls get <call_id> [--coaching]")
        coaching = "--coaching" in args
        return svc.calls_get(args[0], include_coaching=coaching)

    elif command == "calls.stats":
        user_id = get_flag("user") or creds.get("user_id")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.calls_stats(user_id, get_flag("from"), get_flag("to"), days)

    # --- MEETING TRANSCRIPTS (read-only) ---
    elif command == "transcripts.list":
        user_id = get_flag("user")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.meeting_transcripts_list(user_id, get_flag("from"), get_flag("to"), days)

    elif command == "transcripts.get":
        if not args:
            return format_error("Usage: nm nextcall transcripts get <transcript_id>")
        return svc.meeting_transcripts_get(args[0])

    elif command == "transcripts.recent":
        contact_id = get_flag("contact")
        contact_email = get_flag("email")
        user_id = get_flag("user")
        return svc.meeting_transcripts_recent(contact_id, contact_email, user_id)
    elif command == "send.whatsapp":
        limit = profile.get_limit("nextcall", "whatsapp")
        if not tracker.check_and_increment("whatsapp", limit):
            from nm.core.output import format_limit_hit
            return format_limit_hit("whatsapp", tracker.get_count("whatsapp"), limit)
        if len(args) < 2:
            return format_error('Usage: nm nextcall send whatsapp <phone> "message"')
        return svc.send_whatsapp(args[0], " ".join(args[1:]), max_length=max_msg_len)
    elif command == "send.sms":
        limit = profile.get_limit("nextcall", "sms")
        if not tracker.check_and_increment("sms", limit):
            from nm.core.output import format_limit_hit
            return format_limit_hit("sms", tracker.get_count("sms"), limit)
        if len(args) < 2:
            return format_error('Usage: nm nextcall send sms <phone> "message"')
        return svc.send_sms(args[0], " ".join(args[1:]), max_length=max_msg_len)
    elif command == "send.email":
        limit = profile.get_limit("nextcall", "emails")
        if not tracker.check_and_increment("emails", limit):
            from nm.core.output import format_limit_hit
            return format_limit_hit("emails", tracker.get_count("emails"), limit)
        email = args[0] if args else None
        subject, body = "", ""
        i = 1
        while i < len(args):
            if args[i] == "--subject" and i + 1 < len(args):
                subject = args[i + 1]; i += 2
            elif args[i] == "--body" and i + 1 < len(args):
                body = args[i + 1]; i += 2
            else:
                i += 1
        if not email or not subject:
            return format_error('Usage: nm nextcall send email <email> --subject "..." --body "..."')
        return svc.send_email(email, subject, body)
    elif command == "calendar.check":
        if not args:
            return format_error("Usage: nm nextcall calendar check <date YYYY-MM-DD>")
        return svc.calendar_check(args[0])
    elif command == "calendar.book":
        if len(args) < 2:
            return format_error('Usage: nm nextcall calendar book <date> <heure> --title "..."')
        date_str, time_str = args[0], args[1]
        title = "Demo Nextmotion"
        for i, a in enumerate(args):
            if a == "--title" and i + 1 < len(args):
                title = args[i + 1]
        return svc.calendar_book(date_str, time_str, title)
    else:
        return format_error(f"Commande NextCall inconnue: {command}")
