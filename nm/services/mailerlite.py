from __future__ import annotations
import json as _json
import requests
from nm.core.output import format_error

MAILERLITE_API_URL = "https://connect.mailerlite.com/api"


class MailerLiteService:
    def __init__(self, api_key: str):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = requests.get(f"{MAILERLITE_API_URL}{path}", headers=self._headers, params=params)
        if not resp.ok:
            raise RuntimeError(f"MailerLite GET {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _post(self, path: str, payload: dict | None = None) -> dict:
        resp = requests.post(f"{MAILERLITE_API_URL}{path}", headers=self._headers, json=payload or {})
        if not resp.ok:
            raise RuntimeError(f"MailerLite POST {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _put(self, path: str, payload: dict | None = None) -> dict:
        resp = requests.put(f"{MAILERLITE_API_URL}{path}", headers=self._headers, json=payload or {})
        if not resp.ok:
            raise RuntimeError(f"MailerLite PUT {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _delete(self, path: str) -> bool:
        resp = requests.delete(f"{MAILERLITE_API_URL}{path}", headers=self._headers)
        if not resp.ok:
            raise RuntimeError(f"MailerLite DELETE {path} -> {resp.status_code}: {resp.text[:300]}")
        return True

    # ================================================================
    # SUBSCRIBERS
    # ================================================================

    def subscribers_count(self) -> str:
        data = self._get("/subscribers", {"limit": 0})
        return f"Total abonnes : {data.get('total', 0)}"

    def subscribers_list(self, status: str | None = None, limit: int = 50, cursor: str | None = None) -> str:
        params = {"limit": limit}
        if status:
            params["filter[status]"] = status
        if cursor:
            params["cursor"] = cursor
        data = self._get("/subscribers", params)
        items = data.get("data", [])
        if not items:
            return "Aucun abonne."
        lines = [f"{len(items)} abonnes :\n"]
        for s in items:
            fields = s.get("fields", {})
            name = fields.get("name", s.get("name", ""))
            lines.append(f"  {s.get('email', '?')} | {name} | {s.get('status', '?')}")
        nxt = (data.get("links", {}).get("next") or "")
        if nxt:
            lines.append(f"\n  (page suivante disponible)")
        return "\n".join(lines)

    def subscriber_get(self, email_or_id: str) -> str:
        data = self._get(f"/subscribers/{email_or_id}")
        d = data.get("data", data)
        fields = d.get("fields", {})
        lines = [
            f"{d.get('email', '?')}",
            f"  Nom: {fields.get('name', d.get('name', 'N/A'))} {fields.get('last_name', '')}".rstrip(),
            f"  Statut: {d.get('status', 'N/A')}",
            f"  Inscrit: {str(d.get('subscribed_at', d.get('created_at', 'N/A')))[:10]}",
            f"  Opens: {d.get('opened_count', 0)} | Clicks: {d.get('clicked_count', 0)}",
        ]
        groups = d.get("groups", [])
        if groups:
            lines.append(f"  Groupes: {', '.join(g.get('name', g.get('id', '?')) for g in groups)}")
        return "\n".join(lines)

    def subscriber_add(self, email: str, name: str | None = None,
                       groups: list | None = None, status: str = "active",
                       fields: dict | None = None, resubscribe: bool = False) -> str:
        payload = {"email": email, "status": status}
        f = fields or {}
        if name:
            f["name"] = name
        if f:
            payload["fields"] = f
        if groups:
            payload["groups"] = groups
        if resubscribe:
            payload["resubscribe"] = True
        data = self._post("/subscribers", payload)
        d = data.get("data", data)
        return f"Abonne ajoute : {d.get('email', email)} (ID: {d.get('id', '?')})"

    def subscriber_update(self, email_or_id: str, fields: dict | None = None,
                          status: str | None = None, groups: list | None = None) -> str:
        payload = {}
        if fields:
            payload["fields"] = fields
        if status:
            payload["status"] = status
        if groups:
            payload["groups"] = groups
        data = self._put(f"/subscribers/{email_or_id}", payload)
        d = data.get("data", data)
        return f"Abonne mis a jour : {d.get('email', email_or_id)}"

    def subscriber_delete(self, email_or_id: str) -> str:
        self._delete(f"/subscribers/{email_or_id}")
        return f"Abonne supprime : {email_or_id}"

    def subscriber_activity(self, email_or_id: str) -> str:
        data = self._get(f"/subscribers/{email_or_id}/activity")
        items = data.get("data", [])
        if not items:
            return f"Aucune activite pour {email_or_id}"
        lines = [f"Activite de {email_or_id} :\n"]
        for a in items[:20]:
            lines.append(f"  {a.get('type', '?')} | {str(a.get('created_at', ''))[:16]} | {a.get('subject', a.get('name', ''))}")
        return "\n".join(lines)

    def subscriber_search(self, query: str, limit: int = 20) -> str:
        data = self._get("/subscribers", {"filter[search]": query, "limit": limit})
        items = data.get("data", [])
        if not items:
            return f"Aucun abonne pour '{query}'"
        lines = [f"{len(items)} abonnes trouves :\n"]
        for s in items:
            fields = s.get("fields", {})
            name = fields.get("name", s.get("name", ""))
            lines.append(f"  {s.get('email', '?')} | {name} | {s.get('status', '?')}")
        return "\n".join(lines)

    def subscribers_import(self, group_id: str, subscribers: list, resubscribe: bool = False) -> str:
        payload = {"group_id": group_id, "subscribers": subscribers}
        if resubscribe:
            payload["resubscribe"] = True
        data = self._post("/subscribers/import", payload)
        return f"Import lance : {len(subscribers)} abonnes vers groupe {group_id}"

    # ================================================================
    # GROUPS
    # ================================================================

    def groups_list(self) -> str:
        data = self._get("/groups", {"limit": 100, "sort": "-created_at"})
        items = data.get("data", [])
        if not items:
            return "Aucun groupe."
        lines = [f"{len(items)} groupes :\n"]
        for g in items:
            lines.append(f"  [{g.get('id', '?')}] {g.get('name', '?')} — {g.get('subscribers_count', 0)} abonnes")
        return "\n".join(lines)

    def group_create(self, name: str) -> str:
        data = self._post("/groups", {"name": name})
        d = data.get("data", data)
        return f"Groupe cree : {d.get('name', name)} (ID: {d.get('id', '?')})"

    def group_delete(self, group_id: str) -> str:
        self._delete(f"/groups/{group_id}")
        return f"Groupe supprime : {group_id}"

    def group_subscribers(self, group_id: str, limit: int = 50) -> str:
        data = self._get(f"/groups/{group_id}/subscribers", {"limit": limit})
        items = data.get("data", [])
        if not items:
            return "Aucun abonne dans ce groupe."
        lines = [f"{len(items)} abonnes dans le groupe :\n"]
        for s in items:
            fields = s.get("fields", {})
            name = fields.get("name", s.get("name", ""))
            lines.append(f"  {s.get('email', '?')} | {name} | {s.get('status', '?')}")
        return "\n".join(lines)

    def group_add_subscriber(self, group_id: str, subscriber_id: str) -> str:
        self._post(f"/subscribers/{subscriber_id}/groups/{group_id}")
        return f"Abonne {subscriber_id} ajoute au groupe {group_id}"

    def group_remove_subscriber(self, group_id: str, subscriber_id: str) -> str:
        self._delete(f"/subscribers/{subscriber_id}/groups/{group_id}")
        return f"Abonne {subscriber_id} retire du groupe {group_id}"

    # ================================================================
    # CAMPAIGNS
    # ================================================================

    def campaigns_list(self, status: str | None = None, limit: int = 25) -> str:
        params = {"limit": limit}
        if status:
            params["filter[status]"] = status
        data = self._get("/campaigns", params)
        items = data.get("data", [])
        if not items:
            return "Aucune campagne."
        lines = [f"{len(items)} campagnes :\n"]
        for c in items:
            stats = c.get("stats", {})
            sent = stats.get("sent", 0)
            opens = stats.get("open_rate", {})
            open_str = opens.get("string", "0%") if isinstance(opens, dict) else f"{opens}%"
            clicks = stats.get("click_rate", {})
            click_str = clicks.get("string", "0%") if isinstance(clicks, dict) else f"{clicks}%"
            lines.append(
                f"  [{c.get('id', '?')}] {c.get('name', '?')} "
                f"| {c.get('status', '?')} | {sent} envoyes | Open: {open_str} | Click: {click_str}"
            )
        return "\n".join(lines)

    def campaign_get(self, campaign_id: str) -> str:
        data = self._get(f"/campaigns/{campaign_id}")
        c = data.get("data", data)
        stats = c.get("stats", {})

        def _rate(field):
            v = stats.get(field, {})
            return v.get("string", "0%") if isinstance(v, dict) else f"{v}%"

        lines = [
            f"Campagne : {c.get('name', '?')}",
            f"  ID: {c.get('id', '?')}",
            f"  Statut: {c.get('status', '?')}",
            f"  Type: {c.get('type', '?')}",
            f"  Cree: {str(c.get('created_at', 'N/A'))[:10]}",
            f"  Envoye: {str(c.get('scheduled_for') or c.get('started_at') or 'N/A')[:16]}",
            f"",
            f"  Stats :",
            f"    Envoyes: {stats.get('sent', 0)}",
            f"    Delivres: {stats.get('deliveries_count', 0)}",
            f"    Ouverts: {stats.get('opens_count', 0)} ({_rate('open_rate')})",
            f"    Clics: {stats.get('clicks_count', 0)} ({_rate('click_rate')})",
            f"    Click-to-open: {_rate('click_to_open_rate')}",
            f"    Desabonnes: {stats.get('unsubscribes_count', 0)} ({_rate('unsubscribe_rate')})",
            f"    Hard bounces: {stats.get('hard_bounces_count', 0)}",
            f"    Soft bounces: {stats.get('soft_bounces_count', 0)}",
        ]
        dashboard = c.get("dashboard_url")
        if dashboard:
            lines.append(f"\n  Dashboard: {dashboard}")
        return "\n".join(lines)

    def campaign_create(self, name: str, subject: str, from_email: str, from_name: str,
                        campaign_type: str = "regular", groups: list | None = None,
                        content: str | None = None) -> str:
        payload = {
            "name": name,
            "type": campaign_type,
            "emails": [{"subject": subject, "from": from_email, "from_name": from_name}],
        }
        if content:
            payload["emails"][0]["content"] = content
        if groups:
            payload["groups"] = groups
        data = self._post("/campaigns", payload)
        d = data.get("data", data)
        return f"Campagne creee : {d.get('name', name)} (ID: {d.get('id', '?')}) — statut: {d.get('status', 'draft')}"

    def campaign_update(self, campaign_id: str, name: str | None = None,
                        subject: str | None = None) -> str:
        payload = {}
        if name:
            payload["name"] = name
        if subject:
            payload["emails"] = [{"subject": subject}]
        data = self._put(f"/campaigns/{campaign_id}", payload)
        d = data.get("data", data)
        return f"Campagne mise a jour : {d.get('name', '?')} (ID: {campaign_id})"

    def campaign_delete(self, campaign_id: str) -> str:
        self._delete(f"/campaigns/{campaign_id}")
        return f"Campagne supprimee : {campaign_id}"

    def campaign_cancel(self, campaign_id: str) -> str:
        data = self._post(f"/campaigns/{campaign_id}/cancel")
        return f"Campagne annulee : {campaign_id}"

    def campaign_schedule(self, campaign_id: str, date: str) -> str:
        data = self._post(f"/campaigns/{campaign_id}/schedule", {"delivery": "scheduled", "schedule": {"date": date}})
        return f"Campagne programmee : {campaign_id} pour {date}"

    def campaign_subscribers(self, campaign_id: str, activity_type: str | None = None, limit: int = 25) -> str:
        params = {"limit": limit}
        if activity_type:
            params["filter[type]"] = activity_type
        data = self._get(f"/campaigns/{campaign_id}/reports/subscriber-activity", params)
        items = data.get("data", [])
        if not items:
            return "Aucune activite abonne."
        lines = [f"{len(items)} activites :\n"]
        for s in items:
            sub = s.get("subscriber", {})
            lines.append(f"  {sub.get('email', '?')} | {s.get('type', '?')} | {str(s.get('created_at', ''))[:16]}")
        return "\n".join(lines)

    # ================================================================
    # AUTOMATIONS
    # ================================================================

    def automations_list(self) -> str:
        data = self._get("/automations", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return "Aucune automation."
        lines = [f"{len(items)} automations :\n"]
        for a in items:
            status = "active" if a.get("enabled") else "paused"
            trigger = "?"
            triggers = a.get("triggers", [])
            if triggers:
                trigger = triggers[0].get("type", "?")
            else:
                trigger = a.get("trigger_type", "?")
            lines.append(
                f"  [{a.get('id', '?')}] {a.get('name', '?')} "
                f"| {status} | {a.get('steps_count', 0)} etapes | trigger: {trigger}"
            )
        return "\n".join(lines)

    def automation_get(self, automation_id: str) -> str:
        data = self._get(f"/automations/{automation_id}")
        a = data.get("data", data)
        stats = a.get("stats", {})
        lines = [
            f"Automation : {a.get('name', '?')}",
            f"  ID: {a.get('id', '?')}",
            f"  Active: {'oui' if a.get('enabled') else 'non'}",
            f"  Etapes: {a.get('steps_count', 0)}",
            f"  Cree: {str(a.get('created_at', 'N/A'))[:10]}",
        ]
        if stats:
            lines.append(f"  Completed: {stats.get('completed_count', 0)}")
            lines.append(f"  Active subs: {stats.get('active_subscribers_count', 0)}")
        return "\n".join(lines)

    def automation_delete(self, automation_id: str) -> str:
        self._delete(f"/automations/{automation_id}")
        return f"Automation supprimee : {automation_id}"

    def automation_activity(self, automation_id: str, status: str = "completed", limit: int = 20) -> str:
        data = self._get(f"/automations/{automation_id}/activity", {"filter[status]": status, "limit": limit})
        items = data.get("data", [])
        if not items:
            return f"Aucune activite ({status}) pour cette automation."
        lines = [f"{len(items)} activites ({status}) :\n"]
        for a in items:
            sub = a.get("subscriber", {})
            lines.append(f"  {sub.get('email', '?')} | {str(a.get('created_at', ''))[:16]}")
        return "\n".join(lines)

    # ================================================================
    # SEGMENTS
    # ================================================================

    def segments_list(self) -> str:
        data = self._get("/segments", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return "Aucun segment."
        lines = [f"{len(items)} segments :\n"]
        for s in items:
            lines.append(f"  [{s.get('id', '?')}] {s.get('name', '?')}")
        return "\n".join(lines)

    def segment_get(self, segment_id: str) -> str:
        data = self._get(f"/segments/{segment_id}")
        s = data.get("data", data)
        lines = [
            f"Segment : {s.get('name', '?')}",
            f"  ID: {s.get('id', '?')}",
            f"  Cree: {str(s.get('created_at', 'N/A'))[:10]}",
        ]
        return "\n".join(lines)

    def segment_create(self, name: str) -> str:
        data = self._post("/segments", {"name": name})
        d = data.get("data", data)
        return f"Segment cree : {d.get('name', name)} (ID: {d.get('id', '?')})"

    def segment_delete(self, segment_id: str) -> str:
        self._delete(f"/segments/{segment_id}")
        return f"Segment supprime : {segment_id}"

    def segment_subscribers(self, segment_id: str, limit: int = 50) -> str:
        data = self._get(f"/segments/{segment_id}/subscribers", {"limit": limit})
        items = data.get("data", [])
        if not items:
            return "Aucun abonne dans ce segment."
        lines = [f"{len(items)} abonnes dans le segment :\n"]
        for s in items:
            fields = s.get("fields", {})
            name = fields.get("name", s.get("name", ""))
            lines.append(f"  {s.get('email', '?')} | {name} | {s.get('status', '?')}")
        return "\n".join(lines)

    # ================================================================
    # FORMS
    # ================================================================

    def forms_list(self, form_type: str = "popup") -> str:
        data = self._get(f"/forms/{form_type}", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return f"Aucun formulaire ({form_type})."
        lines = [f"{len(items)} formulaires ({form_type}) :\n"]
        for f in items:
            lines.append(f"  [{f.get('id', '?')}] {f.get('name', '?')} | {f.get('subscribers_count', 0)} inscrits")
        return "\n".join(lines)

    def form_get(self, form_id: str) -> str:
        data = self._get(f"/forms/{form_id}")
        f = data.get("data", data)
        lines = [
            f"Formulaire : {f.get('name', '?')}",
            f"  ID: {f.get('id', '?')}",
            f"  Type: {f.get('type', '?')}",
            f"  Inscrits: {f.get('subscribers_count', 0)}",
            f"  Cree: {str(f.get('created_at', 'N/A'))[:10]}",
        ]
        return "\n".join(lines)

    def form_create(self, name: str, form_type: str, groups: list) -> str:
        data = self._post(f"/forms/{form_type}", {"name": name, "groups": groups})
        d = data.get("data", data)
        return f"Formulaire cree : {d.get('name', name)} (ID: {d.get('id', '?')})"

    def form_delete(self, form_id: str) -> str:
        self._delete(f"/forms/{form_id}")
        return f"Formulaire supprime : {form_id}"

    def form_subscribers(self, form_id: str, limit: int = 50) -> str:
        data = self._get(f"/forms/{form_id}/subscribers", {"limit": limit})
        items = data.get("data", [])
        if not items:
            return "Aucun inscrit via ce formulaire."
        lines = [f"{len(items)} inscrits via le formulaire :\n"]
        for s in items:
            fields = s.get("fields", {})
            name = fields.get("name", s.get("name", ""))
            lines.append(f"  {s.get('email', '?')} | {name}")
        return "\n".join(lines)

    # ================================================================
    # FIELDS
    # ================================================================

    def fields_list(self) -> str:
        data = self._get("/fields", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return "Aucun champ custom."
        lines = [f"{len(items)} champs :\n"]
        for f in items:
            lines.append(f"  [{f.get('key', '?')}] {f.get('name', '?')} ({f.get('type', '?')})")
        return "\n".join(lines)

    def field_create(self, name: str, field_type: str = "text") -> str:
        data = self._post("/fields", {"name": name, "type": field_type})
        d = data.get("data", data)
        return f"Champ cree : {d.get('name', name)} (key: {d.get('key', '?')}, type: {field_type})"

    def field_update(self, field_id: str, name: str) -> str:
        data = self._put(f"/fields/{field_id}", {"name": name})
        d = data.get("data", data)
        return f"Champ renomme : {d.get('name', name)}"

    def field_delete(self, field_id: str) -> str:
        self._delete(f"/fields/{field_id}")
        return f"Champ supprime : {field_id}"

    # ================================================================
    # WEBHOOKS
    # ================================================================

    def webhooks_list(self) -> str:
        data = self._get("/webhooks")
        items = data.get("data", [])
        if not items:
            return "Aucun webhook."
        lines = [f"{len(items)} webhooks :\n"]
        for w in items:
            events = ", ".join(w.get("events", []))
            lines.append(f"  [{w.get('id', '?')}] {w.get('name', w.get('url', '?'))} | {events} | {'actif' if w.get('enabled') else 'inactif'}")
        return "\n".join(lines)

    def webhook_get(self, webhook_id: str) -> str:
        data = self._get(f"/webhooks/{webhook_id}")
        w = data.get("data", data)
        lines = [
            f"Webhook : {w.get('name', '?')}",
            f"  ID: {w.get('id', '?')}",
            f"  URL: {w.get('url', '?')}",
            f"  Events: {', '.join(w.get('events', []))}",
            f"  Actif: {'oui' if w.get('enabled') else 'non'}",
        ]
        return "\n".join(lines)

    def webhook_create(self, url: str, events: list, name: str | None = None) -> str:
        payload = {"url": url, "events": events}
        if name:
            payload["name"] = name
        data = self._post("/webhooks", payload)
        d = data.get("data", data)
        return f"Webhook cree : {d.get('url', url)} (ID: {d.get('id', '?')})"

    def webhook_delete(self, webhook_id: str) -> str:
        self._delete(f"/webhooks/{webhook_id}")
        return f"Webhook supprime : {webhook_id}"

    def webhook_update(self, webhook_id: str, url: str | None = None,
                       events: list | None = None, enabled: bool | None = None) -> str:
        payload = {}
        if url:
            payload["url"] = url
        if events:
            payload["events"] = events
        if enabled is not None:
            payload["enabled"] = enabled
        data = self._put(f"/webhooks/{webhook_id}", payload)
        d = data.get("data", data)
        return f"Webhook mis a jour : {d.get('id', webhook_id)}"

    # ================================================================
    # EMAIL TEMPLATES
    # ================================================================

    def templates_list(self, search: str | None = None, limit: int = 25) -> str:
        params = {"limit": limit}
        if search:
            params["filter[name]"] = search
        data = self._get("/campaign-templates", params)
        items = data.get("data", [])
        if not items:
            return "Aucun template email."
        lines = [f"{len(items)} templates :\n"]
        for t in items:
            lines.append(f"  [{t.get('id', '?')}] {t.get('name', '?')}")
        return "\n".join(lines)

    # ================================================================
    # BATCH
    # ================================================================

    def batch(self, requests_list: list) -> str:
        data = self._post("/batch", {"requests": requests_list})
        responses = data.get("responses", [])
        lines = [f"{len(responses)} reponses batch :\n"]
        for i, r in enumerate(responses):
            status = r.get("status_code", r.get("code", "?"))
            lines.append(f"  [{i+1}] {status}")
        return "\n".join(lines)


# ================================================================
# CLI HANDLER
# ================================================================

def _parse_flag(args: list, name: str) -> str:
    flag = f"--{name}"
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
    return ""


def _has_flag(args: list, name: str) -> bool:
    return f"--{name}" in args


def _parse_json_flag(args: list, name: str) -> dict | None:
    raw = _parse_flag(args, name)
    if not raw:
        return None
    return _json.loads(raw)


def handle_mailerlite(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("mailerlite")
    svc = MailerLiteService(api_key=creds["api_key"])

    # ============================================================
    # SUBSCRIBERS
    # ============================================================

    if command == "subscribers.count":
        return svc.subscribers_count()

    elif command == "subscribers.list":
        status = _parse_flag(args, "status") or None
        limit = int(_parse_flag(args, "limit") or "50")
        return svc.subscribers_list(status, limit)

    elif command == "subscribers.search":
        if not args:
            return format_error("Usage: nm mailerlite subscribers search <query>")
        limit = int(_parse_flag(args, "limit") or "20")
        return svc.subscriber_search(args[0], limit)

    elif command == "subscriber.get":
        if not args:
            return format_error("Usage: nm mailerlite subscriber get <email_or_id>")
        return svc.subscriber_get(args[0])

    elif command == "subscriber.activity":
        if not args:
            return format_error("Usage: nm mailerlite subscriber activity <email_or_id>")
        return svc.subscriber_activity(args[0])

    elif command == "subscriber.add":
        if not args:
            return format_error('Usage: nm mailerlite subscriber add <email> [--name "..."] [--group <id>] [--resubscribe] --confirm')
        email = args[0]
        name = _parse_flag(args, "name") or None
        group = _parse_flag(args, "group") or None
        groups = [group] if group else None
        resubscribe = _has_flag(args, "resubscribe")
        fields = _parse_json_flag(args, "fields")
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — abonne non ajoute\n"
                f"  Email: {email}\n"
                f"  Nom: {name or '(non specifie)'}\n"
                f"  Groupe: {group or '(aucun)'}\n"
                f"  Resubscribe: {resubscribe}\n"
                f"\n  Ajoutez --confirm pour ajouter reellement."
            )
        return svc.subscriber_add(email, name, groups, fields=fields, resubscribe=resubscribe)

    elif command == "subscriber.update":
        if not args:
            return format_error('Usage: nm mailerlite subscriber update <email_or_id> [--name "..."] [--status active] [--fields \'{"key":"val"}\'] --confirm')
        email_or_id = args[0]
        name = _parse_flag(args, "name")
        status = _parse_flag(args, "status") or None
        fields = _parse_json_flag(args, "fields") or {}
        if name:
            fields["name"] = name
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — abonne non mis a jour\n"
                f"  Abonne: {email_or_id}\n"
                f"  Fields: {fields or '(aucun)'}\n"
                f"  Statut: {status or '(inchange)'}\n"
                f"\n  Ajoutez --confirm pour modifier reellement."
            )
        return svc.subscriber_update(email_or_id, fields=fields or None, status=status)

    elif command == "subscriber.delete":
        if not args:
            return format_error("Usage: nm mailerlite subscriber delete <email_or_id> --confirm")
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — abonne non supprime\n"
                f"  Abonne: {args[0]}\n"
                f"\n  Ajoutez --confirm pour supprimer reellement."
            )
        return svc.subscriber_delete(args[0])

    elif command == "subscribers.import":
        group_id = _parse_flag(args, "group")
        emails_raw = _parse_flag(args, "emails")
        if not group_id or not emails_raw:
            return format_error('Usage: nm mailerlite subscribers import --group <id> --emails "a@b.com,c@d.com" --confirm')
        subscribers = [{"email": e.strip()} for e in emails_raw.split(",")]
        resubscribe = _has_flag(args, "resubscribe")
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — import non lance\n"
                f"  Groupe: {group_id}\n"
                f"  Abonnes: {len(subscribers)}\n"
                f"  Resubscribe: {resubscribe}\n"
                f"\n  Ajoutez --confirm pour importer reellement."
            )
        return svc.subscribers_import(group_id, subscribers, resubscribe)

    # ============================================================
    # GROUPS
    # ============================================================

    elif command == "groups.list":
        return svc.groups_list()

    elif command == "group.create":
        name = _parse_flag(args, "name") or (args[0] if args else "")
        if not name:
            return format_error('Usage: nm mailerlite group create --name "..." --confirm')
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — groupe non cree\n  Nom: {name}\n\n  Ajoutez --confirm pour creer reellement."
        return svc.group_create(name)

    elif command == "group.delete":
        if not args:
            return format_error("Usage: nm mailerlite group delete <group_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — groupe non supprime\n  ID: {args[0]}\n\n  Ajoutez --confirm pour supprimer reellement."
        return svc.group_delete(args[0])

    elif command == "group.subscribers":
        if not args:
            return format_error("Usage: nm mailerlite group subscribers <group_id>")
        limit = int(_parse_flag(args, "limit") or "50")
        return svc.group_subscribers(args[0], limit)

    elif command == "group.add-subscriber":
        if not args:
            return format_error("Usage: nm mailerlite group add-subscriber <group_id> --subscriber <email_or_id> --confirm")
        group_id = args[0]
        subscriber = _parse_flag(args, "subscriber")
        if not subscriber:
            return format_error("--subscriber est requis")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — abonne non ajoute au groupe\n  Groupe: {group_id}\n  Abonne: {subscriber}\n\n  Ajoutez --confirm pour ajouter reellement."
        return svc.group_add_subscriber(group_id, subscriber)

    elif command == "group.remove-subscriber":
        if not args:
            return format_error("Usage: nm mailerlite group remove-subscriber <group_id> --subscriber <email_or_id> --confirm")
        group_id = args[0]
        subscriber = _parse_flag(args, "subscriber")
        if not subscriber:
            return format_error("--subscriber est requis")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — abonne non retire du groupe\n  Groupe: {group_id}\n  Abonne: {subscriber}\n\n  Ajoutez --confirm pour retirer reellement."
        return svc.group_remove_subscriber(group_id, subscriber)

    # ============================================================
    # CAMPAIGNS
    # ============================================================

    elif command == "campaigns.list":
        status = _parse_flag(args, "status") or None
        limit = int(_parse_flag(args, "limit") or "25")
        return svc.campaigns_list(status, limit)

    elif command == "campaign.get":
        if not args:
            return format_error("Usage: nm mailerlite campaign get <campaign_id>")
        return svc.campaign_get(args[0])

    elif command == "campaign.create":
        name = _parse_flag(args, "name")
        subject = _parse_flag(args, "subject")
        from_email = _parse_flag(args, "from")
        from_name = _parse_flag(args, "from-name")
        if not name or not subject or not from_email or not from_name:
            return format_error('Usage: nm mailerlite campaign create --name "..." --subject "..." --from email --from-name "..." [--group <id>] --confirm')
        group = _parse_flag(args, "group")
        groups = [group] if group else None
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — campagne non creee\n"
                f"  Nom: {name}\n  Sujet: {subject}\n  From: {from_name} <{from_email}>\n"
                f"  Groupe: {group or '(tous)'}\n"
                f"\n  Ajoutez --confirm pour creer reellement."
            )
        return svc.campaign_create(name, subject, from_email, from_name, groups=groups)

    elif command == "campaign.update":
        if not args:
            return format_error('Usage: nm mailerlite campaign update <campaign_id> [--name "..."] [--subject "..."] --confirm')
        campaign_id = args[0]
        name = _parse_flag(args, "name") or None
        subject = _parse_flag(args, "subject") or None
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — campagne non modifiee\n  ID: {campaign_id}\n  Nom: {name or '(inchange)'}\n  Sujet: {subject or '(inchange)'}\n\n  Ajoutez --confirm."
        return svc.campaign_update(campaign_id, name, subject)

    elif command == "campaign.delete":
        if not args:
            return format_error("Usage: nm mailerlite campaign delete <campaign_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — campagne non supprimee\n  ID: {args[0]}\n\n  Ajoutez --confirm pour supprimer reellement."
        return svc.campaign_delete(args[0])

    elif command == "campaign.cancel":
        if not args:
            return format_error("Usage: nm mailerlite campaign cancel <campaign_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — campagne non annulee\n  ID: {args[0]}\n\n  Ajoutez --confirm pour annuler reellement."
        return svc.campaign_cancel(args[0])

    elif command == "campaign.schedule":
        if not args:
            return format_error('Usage: nm mailerlite campaign schedule <campaign_id> --date "2026-06-01 10:00:00" --confirm')
        campaign_id = args[0]
        date = _parse_flag(args, "date")
        if not date:
            return format_error("--date est requis (format: YYYY-MM-DD HH:MM:SS)")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — campagne non programmee\n  ID: {campaign_id}\n  Date: {date}\n\n  Ajoutez --confirm."
        return svc.campaign_schedule(campaign_id, date)

    elif command == "campaign.subscribers":
        if not args:
            return format_error("Usage: nm mailerlite campaign subscribers <campaign_id> [--type opened|clicked|unsubscribed]")
        activity_type = _parse_flag(args, "type") or None
        limit = int(_parse_flag(args, "limit") or "25")
        return svc.campaign_subscribers(args[0], activity_type, limit)

    # ============================================================
    # AUTOMATIONS
    # ============================================================

    elif command == "automations.list":
        return svc.automations_list()

    elif command == "automation.get":
        if not args:
            return format_error("Usage: nm mailerlite automation get <automation_id>")
        return svc.automation_get(args[0])

    elif command == "automation.delete":
        if not args:
            return format_error("Usage: nm mailerlite automation delete <automation_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — automation non supprimee\n  ID: {args[0]}\n\n  Ajoutez --confirm."
        return svc.automation_delete(args[0])

    elif command == "automation.activity":
        if not args:
            return format_error("Usage: nm mailerlite automation activity <automation_id> [--status completed|active|canceled|failed]")
        status = _parse_flag(args, "status") or "completed"
        limit = int(_parse_flag(args, "limit") or "20")
        return svc.automation_activity(args[0], status, limit)

    # ============================================================
    # SEGMENTS
    # ============================================================

    elif command == "segments.list":
        return svc.segments_list()

    elif command == "segment.get":
        if not args:
            return format_error("Usage: nm mailerlite segment get <segment_id>")
        return svc.segment_get(args[0])

    elif command == "segment.create":
        name = _parse_flag(args, "name") or (args[0] if args else "")
        if not name:
            return format_error('Usage: nm mailerlite segment create --name "..." --confirm')
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — segment non cree\n  Nom: {name}\n\n  Ajoutez --confirm."
        return svc.segment_create(name)

    elif command == "segment.delete":
        if not args:
            return format_error("Usage: nm mailerlite segment delete <segment_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — segment non supprime\n  ID: {args[0]}\n\n  Ajoutez --confirm."
        return svc.segment_delete(args[0])

    elif command == "segment.subscribers":
        if not args:
            return format_error("Usage: nm mailerlite segment subscribers <segment_id>")
        limit = int(_parse_flag(args, "limit") or "50")
        return svc.segment_subscribers(args[0], limit)

    # ============================================================
    # FORMS
    # ============================================================

    elif command == "forms.list":
        form_type = _parse_flag(args, "type") or "popup"
        return svc.forms_list(form_type)

    elif command == "form.get":
        if not args:
            return format_error("Usage: nm mailerlite form get <form_id>")
        return svc.form_get(args[0])

    elif command == "form.create":
        name = _parse_flag(args, "name")
        form_type = _parse_flag(args, "type") or "popup"
        group = _parse_flag(args, "group")
        if not name or not group:
            return format_error('Usage: nm mailerlite form create --name "..." --type popup --group <id> --confirm')
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — formulaire non cree\n  Nom: {name}\n  Type: {form_type}\n  Groupe: {group}\n\n  Ajoutez --confirm."
        return svc.form_create(name, form_type, [group])

    elif command == "form.delete":
        if not args:
            return format_error("Usage: nm mailerlite form delete <form_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — formulaire non supprime\n  ID: {args[0]}\n\n  Ajoutez --confirm."
        return svc.form_delete(args[0])

    elif command == "form.subscribers":
        if not args:
            return format_error("Usage: nm mailerlite form subscribers <form_id>")
        limit = int(_parse_flag(args, "limit") or "50")
        return svc.form_subscribers(args[0], limit)

    # ============================================================
    # FIELDS
    # ============================================================

    elif command == "fields.list":
        return svc.fields_list()

    elif command == "field.create":
        name = _parse_flag(args, "name") or (args[0] if args else "")
        field_type = _parse_flag(args, "type") or "text"
        if not name:
            return format_error('Usage: nm mailerlite field create --name "..." [--type text|number|date] --confirm')
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — champ non cree\n  Nom: {name}\n  Type: {field_type}\n\n  Ajoutez --confirm."
        return svc.field_create(name, field_type)

    elif command == "field.update":
        if not args:
            return format_error('Usage: nm mailerlite field update <field_id> --name "..." --confirm')
        name = _parse_flag(args, "name")
        if not name:
            return format_error("--name est requis")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — champ non modifie\n  ID: {args[0]}\n  Nouveau nom: {name}\n\n  Ajoutez --confirm."
        return svc.field_update(args[0], name)

    elif command == "field.delete":
        if not args:
            return format_error("Usage: nm mailerlite field delete <field_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — champ non supprime\n  ID: {args[0]}\n\n  Ajoutez --confirm."
        return svc.field_delete(args[0])

    # ============================================================
    # WEBHOOKS
    # ============================================================

    elif command == "webhooks.list":
        return svc.webhooks_list()

    elif command == "webhook.get":
        if not args:
            return format_error("Usage: nm mailerlite webhook get <webhook_id>")
        return svc.webhook_get(args[0])

    elif command == "webhook.create":
        url = _parse_flag(args, "url")
        events_raw = _parse_flag(args, "events")
        name = _parse_flag(args, "name") or None
        if not url or not events_raw:
            return format_error('Usage: nm mailerlite webhook create --url "..." --events "subscriber.created,campaign.sent" [--name "..."] --confirm')
        events = [e.strip() for e in events_raw.split(",")]
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — webhook non cree\n  URL: {url}\n  Events: {', '.join(events)}\n\n  Ajoutez --confirm."
        return svc.webhook_create(url, events, name)

    elif command == "webhook.update":
        if not args:
            return format_error('Usage: nm mailerlite webhook update <webhook_id> [--url "..."] [--events "..."] [--enabled true|false] --confirm')
        webhook_id = args[0]
        url = _parse_flag(args, "url") or None
        events_raw = _parse_flag(args, "events")
        events = [e.strip() for e in events_raw.split(",")] if events_raw else None
        enabled_raw = _parse_flag(args, "enabled")
        enabled = None
        if enabled_raw:
            enabled = enabled_raw.lower() in ("true", "1", "yes")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — webhook non modifie\n  ID: {webhook_id}\n\n  Ajoutez --confirm."
        return svc.webhook_update(webhook_id, url, events, enabled)

    elif command == "webhook.delete":
        if not args:
            return format_error("Usage: nm mailerlite webhook delete <webhook_id> --confirm")
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — webhook non supprime\n  ID: {args[0]}\n\n  Ajoutez --confirm."
        return svc.webhook_delete(args[0])

    # ============================================================
    # TEMPLATES
    # ============================================================

    elif command == "templates.list":
        search = _parse_flag(args, "search") or None
        limit = int(_parse_flag(args, "limit") or "25")
        return svc.templates_list(search, limit)

    # ============================================================
    # BATCH
    # ============================================================

    elif command == "batch":
        raw = _parse_flag(args, "requests")
        if not raw:
            return format_error('Usage: nm mailerlite batch --requests \'[{"method":"GET","path":"api/subscribers"}]\' --confirm')
        reqs = _json.loads(raw)
        if not _has_flag(args, "confirm"):
            return f"DRY RUN — batch non execute\n  Requetes: {len(reqs)}\n\n  Ajoutez --confirm."
        return svc.batch(reqs)

    else:
        return format_error(f"Commande MailerLite inconnue: {command}")
