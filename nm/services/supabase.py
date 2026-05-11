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

    def _post(self, table: str, data: dict) -> dict:
        resp = requests.post(
            f"{self._url}/rest/v1/{table}",
            headers={**self._headers, "Prefer": "return=representation"},
            json=data,
        )
        resp.raise_for_status()
        result = resp.json()
        return result[0] if isinstance(result, list) else result

    def sessions_save(self, summary: str, source: str = "telegram_agent",
                      agent_name: str = "") -> str:
        """Save a session summary — used by VPS agents to sync memory."""
        session = self._post("sessions", {
            "telegram_chat_id": 0,
            "ended_by": "agent_sync",
            "source": source,
            "ended_at": datetime.utcnow().isoformat(),
        })
        session_id = session.get("id", "?")

        # Save summary as assistant message
        self._post("messages", {
            "session_id": session_id,
            "role": "assistant",
            "content": summary,
        })

        return f"Session sauvegardee — ID: {session_id} | Source: {source}" + \
               (f" | Agent: {agent_name}" if agent_name else "")

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

    # ── Video tasks (queue Anna → Mac cabinet) ──

    def video_tasks_create(self, brief: str, platform: str = "instagram",
                           source_url: str = "", style: str = "",
                           duration: int = 0, aspect: str = "9:16",
                           monday_item_id: str = "",
                           created_by: str = "anna") -> str:
        data = {
            "brief": brief,
            "platform": platform,
            "status": "pending",
            "created_by": created_by,
            "aspect_ratio": aspect,
        }
        if source_url:
            data["source_url"] = source_url
        if style:
            data["style"] = style
        if duration:
            data["target_duration"] = duration
        if monday_item_id:
            data["monday_item_id"] = monday_item_id

        resp = requests.post(
            f"{self._url}/rest/v1/video_tasks",
            headers={**self._headers, "Prefer": "return=representation"},
            json=data,
        )
        resp.raise_for_status()
        result = resp.json()
        task = result[0] if isinstance(result, list) else result
        return f"Video task creee — ID: {task.get('id', '?')} | Platform: {platform} | Status: pending"

    def video_tasks_list(self, status: str = "", limit: int = 10) -> str:
        params = {
            "order": "created_at.desc",
            "limit": limit,
            "select": "id,created_at,created_by,brief,platform,status,style,target_duration",
        }
        if status:
            params["status"] = f"eq.{status}"
        tasks = self._get("video_tasks", params)
        if not tasks:
            return "Aucune video task" + (f" ({status})" if status else "") + "."
        lines = [f"{len(tasks)} video tasks :\n"]
        for t in tasks:
            created = (t.get("created_at", "") or "")[:16].replace("T", " ")
            dur = f"{t.get('target_duration', '?')}s" if t.get("target_duration") else "?"
            lines.append(
                f"  [{t.get('status', '?')}] {t.get('brief', '?')[:80]}"
            )
            lines.append(
                f"    ID: {t.get('id', '?')[:8]}... | {t.get('platform', '?')} | "
                f"{t.get('style', '')} | {dur} | par {t.get('created_by', '?')} | {created}"
            )
        return "\n".join(lines)

    def video_tasks_get(self, task_id: str) -> str:
        tasks = self._get("video_tasks", {"id": f"eq.{task_id}"})
        if not tasks:
            return format_error(f"Video task {task_id} introuvable")
        t = tasks[0]
        lines = [
            f"Video task {t.get('id', '?')}",
            f"  Status: {t.get('status', '?')}",
            f"  Brief: {t.get('brief', '?')}",
            f"  Platform: {t.get('platform', '?')}",
            f"  Style: {t.get('style', 'N/A')}",
            f"  Duration: {t.get('target_duration', 'N/A')}s",
            f"  Aspect: {t.get('aspect_ratio', 'N/A')}",
            f"  Source: {t.get('source_url', 'N/A')}",
            f"  Output: {t.get('output_url', 'N/A')}",
            f"  Monday item: {t.get('monday_item_id', 'N/A')}",
            f"  Created by: {t.get('created_by', '?')}",
            f"  Created: {(t.get('created_at', '') or '')[:16]}",
        ]
        if t.get("error"):
            lines.append(f"  Error: {t['error']}")
        if t.get("processing_started_at"):
            lines.append(f"  Processing started: {t['processing_started_at'][:16]}")
        if t.get("processing_completed_at"):
            lines.append(f"  Processing completed: {t['processing_completed_at'][:16]}")
        return "\n".join(lines)

    def video_tasks_update(self, task_id: str, updates: dict) -> str:
        resp = requests.patch(
            f"{self._url}/rest/v1/video_tasks?id=eq.{task_id}",
            headers={**self._headers, "Prefer": "return=representation"},
            json=updates,
        )
        resp.raise_for_status()
        return f"Video task {task_id} mise a jour"

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

    elif command == "sessions.save":
        summary = _flag("summary")
        if not summary and args:
            summary = " ".join([a for a in args if not a.startswith("--")])
        if not summary:
            return format_error('Usage: nm supabase sessions save --summary "Resume de la session" [--source telegram_anna] [--agent anna]')
        source = _flag("source") or "telegram_agent"
        agent = _flag("agent") or ""
        return svc.sessions_save(summary, source, agent)

    elif command == "messages.search":
        if not args:
            return format_error('Usage: nm supabase messages search "keyword" [--days 30]')
        query = args[0]
        days = int(_flag("days") or "30")
        limit = int(_flag("limit") or "10")
        return svc.messages_search(query, days, limit)

    # Video tasks
    elif command == "video-tasks.create":
        brief = _flag("brief")
        if not brief and args:
            brief = args[0]
        if not brief:
            return format_error('Usage: nm supabase video-tasks create --brief "..." --platform instagram [--source "url"] [--style kinetic] [--duration 30]')
        return svc.video_tasks_create(
            brief=brief,
            platform=_flag("platform") or "instagram",
            source_url=_flag("source"),
            style=_flag("style"),
            duration=int(_flag("duration") or "0"),
            aspect=_flag("aspect") or "9:16",
            monday_item_id=_flag("monday-item"),
            created_by=_flag("by") or "anna",
        )

    elif command == "video-tasks.list":
        status = _flag("status")
        limit = int(_flag("limit") or "10")
        return svc.video_tasks_list(status, limit)

    elif command == "video-tasks.get":
        if not args:
            return format_error("Usage: nm supabase video-tasks get <task_id>")
        return svc.video_tasks_get(args[0])

    elif command == "video-tasks.update":
        if not args:
            return format_error("Usage: nm supabase video-tasks update <task_id> --status done [--output-url ...]")
        task_id = args[0]
        updates = {}
        for field in ["status", "output-url", "output-path", "error", "notes"]:
            val = _flag(field)
            if val:
                key = field.replace("-", "_")
                updates[key] = val
        if not updates:
            return format_error("Rien a mettre a jour. Utiliser --status, --output-url, --error, --notes")
        return svc.video_tasks_update(task_id, updates)

    else:
        return format_error(f"Commande Supabase inconnue: {command}")
