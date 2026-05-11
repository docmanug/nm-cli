from __future__ import annotations
from datetime import datetime, timedelta
import requests
from nm.core.output import format_error


class SupabaseService:
    def __init__(self, url: str, service_key: str):
        self._url = url.rstrip("/")
        self._headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }

    def _get(self, table: str, params: dict | None = None) -> list:
        resp = requests.get(
            f"{self._url}/rest/v1/{table}",
            headers=self._headers,
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()

    def sessions_list(self, days: int = 7, source: str = "",
                      limit: int = 20) -> str:
        params = {
            "order": "started_at.desc",
            "limit": limit,
            "select": "id,started_at,source,ended_by",
        }
        if days > 0:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            params["started_at"] = f"gte.{cutoff}"
        if source:
            params["source"] = f"eq.{source}"

        sessions = self._get("sessions", params)
        if not sessions:
            return f"Aucune session (derniers {days}j)."
        lines = [f"{len(sessions)} sessions (derniers {days}j) :\n"]
        for s in sessions:
            started = (s.get("started_at", "") or "")[:16].replace("T", " ")
            lines.append(
                f"  [{s.get('source', '?')}] {started} — {s.get('ended_by', '?')}"
            )
        return "\n".join(lines)

    def sessions_get(self, session_id: str) -> str:
        # Get session
        sessions = self._get("sessions", {
            "id": f"eq.{session_id}",
            "select": "id,started_at,source,ended_by",
        })
        if not sessions:
            return format_error(f"Session {session_id} introuvable")
        session = sessions[0]

        # Get messages
        messages = self._get("messages", {
            "session_id": f"eq.{session_id}",
            "order": "created_at.asc",
            "select": "role,content,created_at",
        })

        started = (session.get("started_at", "") or "")[:16].replace("T", " ")
        lines = [
            f"Session {session_id}",
            f"  Source: {session.get('source', '?')}",
            f"  Date: {started}",
            f"  Statut: {session.get('ended_by', '?')}",
            f"  Messages: {len(messages)}",
            "",
        ]
        for m in messages:
            role = m.get("role", "?")
            content = (m.get("content", "") or "")
            lines.append(f"  [{role}] {content[:500]}")
            if len(content) > 500:
                lines.append(f"  ... ({len(content)} chars total)")
            lines.append("")
        return "\n".join(lines)

    def sessions_summaries(self, days: int = 7, limit: int = 10) -> str:
        """Get recent session summaries — the assistant's last message per session."""
        params = {
            "order": "started_at.desc",
            "limit": limit,
            "select": "id,started_at,source",
        }
        if days > 0:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            params["started_at"] = f"gte.{cutoff}"

        sessions = self._get("sessions", params)
        if not sessions:
            return f"Aucune session (derniers {days}j)."

        lines = [f"Resumes des {len(sessions)} dernieres sessions ({days}j) :\n"]
        for s in sessions:
            sid = s["id"]
            started = (s.get("started_at", "") or "")[:16].replace("T", " ")
            source = s.get("source", "?")

            # Get the last assistant message (usually the summary)
            msgs = self._get("messages", {
                "session_id": f"eq.{sid}",
                "role": "eq.assistant",
                "order": "created_at.desc",
                "limit": 1,
                "select": "content",
            })

            summary = "Pas de resume"
            if msgs:
                summary = (msgs[0].get("content", "") or "")[:300]

            lines.append(f"  [{source}] {started}")
            lines.append(f"    {summary}")
            lines.append("")
        return "\n".join(lines)

    def messages_search(self, query: str, days: int = 30,
                        limit: int = 10) -> str:
        """Search messages containing a keyword."""
        params = {
            "content": f"ilike.*{query}*",
            "order": "created_at.desc",
            "limit": limit,
            "select": "session_id,role,content,created_at",
        }
        if days > 0:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            params["created_at"] = f"gte.{cutoff}"

        messages = self._get("messages", params)
        if not messages:
            return f"Aucun message contenant '{query}' (derniers {days}j)."
        lines = [f"{len(messages)} messages contenant '{query}' :\n"]
        for m in messages:
            date = (m.get("created_at", "") or "")[:16].replace("T", " ")
            role = m.get("role", "?")
            content = (m.get("content", "") or "")[:200]
            lines.append(f"  [{date}] ({role}) {content}")
            lines.append("")
        return "\n".join(lines)


def handle_supabase(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("supabase")
    svc = SupabaseService(
        url=creds["url"],
        service_key=creds["service_key"],
    )

    def _flag(name):
        for i, a in enumerate(args):
            if a == f"--{name}" and i + 1 < len(args):
                return args[i + 1]
        return ""

    if command == "sessions.list":
        days = int(_flag("days") or "7")
        source = _flag("source")
        limit = int(_flag("limit") or "20")
        return svc.sessions_list(days, source, limit)

    elif command == "sessions.get":
        if not args:
            return format_error("Usage: nm supabase sessions get <session_id>")
        return svc.sessions_get(args[0])

    elif command == "sessions.summaries":
        days = int(_flag("days") or "7")
        limit = int(_flag("limit") or "10")
        return svc.sessions_summaries(days, limit)

    elif command == "messages.search":
        if not args:
            return format_error('Usage: nm supabase messages search "keyword" [--days 30]')
        query = args[0]
        days = int(_flag("days") or "30")
        limit = int(_flag("limit") or "10")
        return svc.messages_search(query, days, limit)

    else:
        return format_error(f"Commande Supabase inconnue: {command}")
