from __future__ import annotations
from datetime import date, datetime, timedelta
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

    # --- SMS (read-only) ---

    def sms_list(self, user_id: str | None = None,
                 contact_id: str | None = None,
                 date_from: str | None = None,
                 date_to: str | None = None,
                 days: int | None = None) -> str:
        params = {}
        if user_id:
            params["userId"] = user_id
        if contact_id:
            params["contactId"] = contact_id
        if days and not date_from:

            date_from = (date.today() - timedelta(days=days)).isoformat()
            date_to = date.today().isoformat()
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        result = self._call_tool("sms_list", params)
        messages = result if isinstance(result, list) else result.get("messages", [])
        if not messages:
            return "Aucun SMS."
        lines = [f"{len(messages)} SMS :\n"]
        for i, m in enumerate(messages, 1):
            direction = m.get("direction", "?")
            body = (m.get("body", "") or "")[:100]
            dt = (m.get("date", m.get("createdAt", "?"))[:16]
                  if m.get("date", m.get("createdAt")) else "?")
            contact = m.get("contactName", m.get("contact", {}).get("name", m.get("contactId", "?")))
            lines.append(f"#{i} [{dt}] {direction} {contact}: {body}")
        return "\n".join(lines)

    # --- WHATSAPP (read-only) ---

    def whatsapp_list(self, user_id: str | None = None,
                      contact_id: str | None = None,
                      date_from: str | None = None,
                      date_to: str | None = None,
                      days: int | None = None) -> str:
        params = {}
        if user_id:
            params["userId"] = user_id
        if contact_id:
            params["contactId"] = contact_id
        if days and not date_from:

            date_from = (date.today() - timedelta(days=days)).isoformat()
            date_to = date.today().isoformat()
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        result = self._call_tool("whatsapp_list", params)
        messages = result if isinstance(result, list) else result.get("messages", [])
        if not messages:
            return "Aucun message WhatsApp."
        lines = [f"{len(messages)} messages WhatsApp :\n"]
        for i, m in enumerate(messages, 1):
            direction = m.get("direction", "?")
            body = (m.get("body", "") or "")[:100]
            dt = (m.get("date", m.get("createdAt", "?"))[:16]
                  if m.get("date", m.get("createdAt")) else "?")
            contact = m.get("contactName", m.get("contact", {}).get("name", m.get("contactId", "?")))
            lines.append(f"#{i} [{dt}] {direction} {contact}: {body}")
        return "\n".join(lines)

    # --- GMAIL (read-only) ---

    def gmail_list(self, user_id: str, contact_email: str | None = None,
                   max_results: int = 10) -> str:
        params = {"userId": user_id}
        if contact_email:
            params["contactEmail"] = contact_email
        if max_results:
            params["maxResults"] = max_results
        result = self._call_tool("gmail_list", params)
        emails = result if isinstance(result, list) else result.get("emails", result.get("messages", []))
        if not emails:
            return "Aucun email."
        lines = [f"{len(emails)} emails :\n"]
        for i, e in enumerate(emails, 1):
            subject = e.get("subject", "(sans objet)")
            sender = e.get("from", e.get("sender", "?"))
            dt = (e.get("date", e.get("receivedAt", "?"))[:16]
                  if e.get("date", e.get("receivedAt")) else "?")
            lines.append(f"#{i} [{dt}] {sender}: {subject}")
        return "\n".join(lines)

    def gmail_get(self, user_id: str, message_id: str) -> str:
        result = self._call_tool("gmail_get", {"userId": user_id, "messageId": message_id})
        e = result if isinstance(result, dict) else {}
        lines = [
            f"Email #{e.get('id', message_id)}",
            f"  De: {e.get('from', e.get('sender', 'N/A'))}",
            f"  A: {e.get('to', 'N/A')}",
            f"  Date: {e.get('date', 'N/A')}",
            f"  Objet: {e.get('subject', 'N/A')}",
            f"  Corps:\n    {(e.get('body', e.get('text', '')) or '')[:3000]}",
        ]
        return "\n".join(lines)

    # --- TEAM (read-only) ---

    def team_get(self, user_id: str, metrics_date: str | None = None) -> str:
        params = {"userId": user_id}
        if metrics_date:
            params["metricsDate"] = metrics_date
        result = self._call_tool("team_get", params)
        t = result if isinstance(result, dict) else {}
        metrics = t.get("metrics", t)
        lines = [
            f"Profil {t.get('name', t.get('email', user_id))}",
            f"  Statut: {'En ligne' if t.get('online') else 'Hors ligne'}",
            f"  Appels: {metrics.get('calls', metrics.get('totalCalls', 0))}",
            f"  Connectes: {metrics.get('connected', metrics.get('connectedCalls', 0))}",
            f"  RDV pris: {metrics.get('meetings', metrics.get('meetingsBooked', 0))}",
            f"  SMS envoyes: {metrics.get('sms', metrics.get('smsSent', 0))}",
            f"  WA envoyes: {metrics.get('whatsapp', metrics.get('whatsappSent', 0))}",
            f"  Duree totale: {metrics.get('totalDuration', metrics.get('duration', 0))}s",
        ]
        return "\n".join(lines)

    def team_list(self) -> str:
        result = self._call_tool("team_list", {})
        members = result if isinstance(result, list) else result.get("members", [])
        if not members:
            return "Aucun membre."
        lines = [f"{len(members)} membres :\n"]
        for m in members:
            status = "En ligne" if m.get("online") else "Hors ligne"
            lines.append(f"  {m.get('name', '?')} (ID: {m.get('id', '?')}) — {status}")
        return "\n".join(lines)

    # --- NOTIFICATIONS (read-only) ---

    def notifications_get(self, user_id: str | None = None) -> str:
        params = {}
        if user_id:
            params["userId"] = user_id
        result = self._call_tool("notifications_get", params)
        n = result if isinstance(result, dict) else {}
        missed = n.get("missedCalls", n.get("missed_calls", []))
        unread = n.get("unreadMessages", n.get("unread_messages", []))
        lines = []
        if missed:
            lines.append(f"{len(missed)} appels manques :")
            for m in missed[:10]:
                contact = m.get("contactName", m.get("contact", {}).get("name", "?"))
                dt = (m.get("date", m.get("createdAt", "?"))[:16]
                      if m.get("date", m.get("createdAt")) else "?")
                lines.append(f"  [{dt}] {contact} — {m.get('phone', '?')}")
        if unread:
            lines.append(f"\n{len(unread)} messages non lus :")
            for m in unread[:10]:
                contact = m.get("contactName", m.get("contact", {}).get("name", "?"))
                channel = m.get("channel", m.get("type", "?"))
                lines.append(f"  {contact} — {channel}")
        if not lines:
            return "Aucune notification en attente."
        return "\n".join(lines)

    def messages_unread(self, user_id: str | None = None) -> str:
        params = {}
        if user_id:
            params["userId"] = user_id
        result = self._call_tool("messages_unread", params)
        r = result if isinstance(result, dict) else {}
        sms = r.get("sms", 0)
        wa = r.get("whatsapp", 0)
        total = r.get("total", sms + wa)
        return f"Messages non lus : {total} (SMS: {sms}, WhatsApp: {wa})"

    # --- CALENDAR EVENTS (read-only) ---

    def calendar_events(self, user_id: str, date_str: str | None = None,
                        days: int | None = None) -> str:
        if not date_str:
            date_str = date.today().isoformat()
        time_min = f"{date_str}T00:00:00"
        if days:
            end_date = (datetime.strptime(date_str, "%Y-%m-%d").date()
                        + timedelta(days=days)).isoformat()
        else:
            end_date = date_str
        time_max = f"{end_date}T23:59:59"

        result = self._call_tool("calendar_events", {
            "userId": user_id,
            "timeMin": time_min,
            "timeMax": time_max,
        })
        events = result if isinstance(result, list) else result.get("events", [])
        if not events:
            return f"Aucun evenement le {date_str}."
        lines = [f"{len(events)} evenements :\n"]
        for e in events:
            start = e.get("start", {})
            start_time = start.get("dateTime", start.get("date", "?"))
            if "T" in str(start_time):
                start_time = start_time[11:16]
            end = e.get("end", {})
            end_time = end.get("dateTime", end.get("date", "?"))
            if "T" in str(end_time):
                end_time = end_time[11:16]
            summary = e.get("summary", "(sans titre)")
            attendees = ", ".join([a.get("email", "?") for a in e.get("attendees", [])])
            lines.append(f"  {start_time}-{end_time} {summary}")
            if attendees:
                lines.append(f"    Avec: {attendees}")
        return "\n".join(lines)

    # --- COACH IA (read-only) ---

    def coach_tips(self, call_id: str) -> str:
        result = self._call_tool("coach_tips_for_call", {"callId": call_id})
        tips = result if isinstance(result, list) else result.get("tips", [])
        if not tips:
            return "Aucun tip de coaching pour cet appel."
        lines = ["Tips coaching :\n"]
        for i, tip in enumerate(tips, 1):
            if isinstance(tip, dict):
                lines.append(f"  {i}. {tip.get('text', tip.get('tip', str(tip)))}")
            else:
                lines.append(f"  {i}. {tip}")
        return "\n".join(lines)

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

    # --- SMS (read-only) ---
    elif command == "sms.list":
        user_id = get_flag("user")
        contact_id = get_flag("contact")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.sms_list(user_id, contact_id, get_flag("from"), get_flag("to"), days)

    # --- WHATSAPP (read-only) ---
    elif command == "whatsapp.list":
        user_id = get_flag("user")
        contact_id = get_flag("contact")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.whatsapp_list(user_id, contact_id, get_flag("from"), get_flag("to"), days)

    # --- GMAIL (read-only) ---
    elif command == "gmail.list":
        user_id = get_flag("user") or creds.get("user_id")
        contact_email = get_flag("email")
        max_str = get_flag("max")
        max_results = int(max_str) if max_str else 10
        return svc.gmail_list(user_id, contact_email, max_results)

    elif command == "gmail.get":
        if not args:
            return format_error("Usage: nm nextcall gmail get <message_id> [--user <id>]")
        user_id = get_flag("user") or creds.get("user_id")
        return svc.gmail_get(user_id, args[0])

    # --- TEAM (read-only) ---
    elif command == "team.get":
        user_id = get_flag("user") or (args[0] if args else creds.get("user_id"))
        metrics_date = get_flag("date")
        return svc.team_get(user_id, metrics_date)

    elif command == "team.list":
        return svc.team_list()

    # --- NOTIFICATIONS (read-only) ---
    elif command == "notifications.get":
        user_id = get_flag("user")
        return svc.notifications_get(user_id)

    elif command == "messages.unread":
        user_id = get_flag("user")
        return svc.messages_unread(user_id)

    # --- CALENDAR EVENTS (read-only) ---
    elif command == "calendar.events":
        user_id = get_flag("user") or creds.get("user_id")
        date_str = get_flag("date")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.calendar_events(user_id, date_str, days)

    # --- COACH IA ---
    elif command == "coach.tips":
        if not args:
            return format_error("Usage: nm nextcall coach tips <call_id>")
        return svc.coach_tips(args[0])
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
