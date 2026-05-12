from __future__ import annotations
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
        resp = requests.get(
            f"{MAILERLITE_API_URL}{path}",
            headers=self._headers,
            params=params,
        )
        if not resp.ok:
            raise RuntimeError(f"MailerLite GET {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _post(self, path: str, payload: dict | None = None) -> dict:
        resp = requests.post(
            f"{MAILERLITE_API_URL}{path}",
            headers=self._headers,
            json=payload or {},
        )
        if not resp.ok:
            raise RuntimeError(f"MailerLite POST {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _put(self, path: str, payload: dict | None = None) -> dict:
        resp = requests.put(
            f"{MAILERLITE_API_URL}{path}",
            headers=self._headers,
            json=payload or {},
        )
        if not resp.ok:
            raise RuntimeError(f"MailerLite PUT {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _delete(self, path: str) -> bool:
        resp = requests.delete(
            f"{MAILERLITE_API_URL}{path}",
            headers=self._headers,
        )
        if not resp.ok:
            raise RuntimeError(f"MailerLite DELETE {path} -> {resp.status_code}: {resp.text[:300]}")
        return True

    # --- Subscribers ---

    def subscribers_count(self) -> str:
        data = self._get("/subscribers", {"limit": 0})
        total = data.get("total", 0)
        return f"Total abonnes : {total}"

    def subscriber_get(self, email_or_id: str) -> str:
        data = self._get(f"/subscribers/{email_or_id}")
        d = data.get("data", data)
        fields = d.get("fields", {})
        lines = [
            f"{d.get('email', '?')}",
            f"  Nom: {fields.get('name', d.get('name', 'N/A'))} {fields.get('last_name', '')}".rstrip(),
            f"  Statut: {d.get('status', 'N/A')}",
            f"  Inscrit: {d.get('subscribed_at', d.get('created_at', 'N/A'))[:10]}",
            f"  Opens: {d.get('opened_count', 0)} | Clicks: {d.get('clicked_count', 0)}",
        ]
        groups = d.get("groups", [])
        if groups:
            lines.append(f"  Groupes: {', '.join(g.get('name', g.get('id', '?')) for g in groups)}")
        return "\n".join(lines)

    def subscriber_add(self, email: str, name: str | None = None,
                       groups: list | None = None, status: str = "active") -> str:
        payload = {"email": email, "status": status}
        if name:
            payload["fields"] = {"name": name}
        if groups:
            payload["groups"] = groups
        data = self._post("/subscribers", payload)
        d = data.get("data", data)
        return f"Abonne ajoute : {d.get('email', email)} (ID: {d.get('id', '?')})"

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

    # --- Groups ---

    def groups_list(self) -> str:
        data = self._get("/groups", {"limit": 100, "sort": "-created_at"})
        items = data.get("data", [])
        if not items:
            return "Aucun groupe."
        lines = [f"{len(items)} groupes :\n"]
        for g in items:
            lines.append(
                f"  [{g.get('id', '?')}] {g.get('name', '?')} "
                f"— {g.get('subscribers_count', 0)} abonnes"
            )
        return "\n".join(lines)

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

    # --- Campaigns ---

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
            f"  Cree: {c.get('created_at', 'N/A')[:10]}",
            f"  Envoye: {c.get('scheduled_for', c.get('started_at', 'N/A'))[:16] if c.get('scheduled_for') or c.get('started_at') else 'N/A'}",
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

    # --- Automations ---

    def automations_list(self) -> str:
        data = self._get("/automations", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return "Aucune automation."
        lines = [f"{len(items)} automations :\n"]
        for a in items:
            status = "active" if a.get("enabled") else "paused"
            lines.append(
                f"  [{a.get('id', '?')}] {a.get('name', '?')} "
                f"| {status} | {a.get('steps_count', 0)} etapes | trigger: {a.get('triggers', [{}])[0].get('type', '?') if a.get('triggers') else a.get('trigger_type', '?')}"
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
            f"  Cree: {a.get('created_at', 'N/A')[:10]}",
        ]
        if stats:
            lines.append(f"  Completed: {stats.get('completed_count', 0)}")
            lines.append(f"  Active subs: {stats.get('active_subscribers_count', 0)}")
        return "\n".join(lines)

    # --- Segments ---

    def segments_list(self) -> str:
        data = self._get("/segments", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return "Aucun segment."
        lines = [f"{len(items)} segments :\n"]
        for s in items:
            lines.append(f"  [{s.get('id', '?')}] {s.get('name', '?')}")
        return "\n".join(lines)

    # --- Forms ---

    def forms_list(self, form_type: str = "popup") -> str:
        data = self._get(f"/forms/{form_type}", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return f"Aucun formulaire ({form_type})."
        lines = [f"{len(items)} formulaires ({form_type}) :\n"]
        for f in items:
            lines.append(
                f"  [{f.get('id', '?')}] {f.get('name', '?')} "
                f"| {f.get('subscribers_count', 0)} inscrits"
            )
        return "\n".join(lines)

    # --- Fields ---

    def fields_list(self) -> str:
        data = self._get("/fields", {"limit": 100})
        items = data.get("data", [])
        if not items:
            return "Aucun champ custom."
        lines = [f"{len(items)} champs :\n"]
        for f in items:
            lines.append(f"  [{f.get('key', '?')}] {f.get('name', '?')} ({f.get('type', '?')})")
        return "\n".join(lines)


def _parse_flag(args: list, name: str) -> str:
    flag = f"--{name}"
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
    return ""


def _has_flag(args: list, name: str) -> bool:
    return f"--{name}" in args


def handle_mailerlite(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("mailerlite")
    svc = MailerLiteService(api_key=creds["api_key"])

    # --- Subscribers ---

    if command == "subscribers.count":
        return svc.subscribers_count()

    elif command == "subscribers.search":
        if not args:
            return format_error("Usage: nm mailerlite subscribers search <query>")
        limit = int(_parse_flag(args, "limit") or "20")
        return svc.subscriber_search(args[0], limit)

    elif command == "subscriber.get":
        if not args:
            return format_error("Usage: nm mailerlite subscriber get <email_or_id>")
        return svc.subscriber_get(args[0])

    elif command == "subscriber.add":
        if not args:
            return format_error('Usage: nm mailerlite subscriber add <email> [--name "..."] [--group <id>] --confirm')
        email = args[0]
        name = _parse_flag(args, "name") or None
        group = _parse_flag(args, "group") or None
        groups = [group] if group else None
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — abonne non ajoute\n"
                f"  Email: {email}\n"
                f"  Nom: {name or '(non specifie)'}\n"
                f"  Groupe: {group or '(aucun)'}\n"
                f"\n  Ajoutez --confirm pour ajouter reellement."
            )
        return svc.subscriber_add(email, name, groups)

    # --- Groups ---

    elif command == "groups.list":
        return svc.groups_list()

    elif command == "group.subscribers":
        if not args:
            return format_error("Usage: nm mailerlite group subscribers <group_id>")
        limit = int(_parse_flag(args, "limit") or "50")
        return svc.group_subscribers(args[0], limit)

    elif command == "group.add-subscriber":
        if len(args) < 2 and not _parse_flag(args, "subscriber"):
            return format_error("Usage: nm mailerlite group add-subscriber <group_id> --subscriber <email_or_id> --confirm")
        group_id = args[0]
        subscriber = _parse_flag(args, "subscriber")
        if not subscriber:
            return format_error("--subscriber est requis")
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — abonne non ajoute au groupe\n"
                f"  Groupe: {group_id}\n"
                f"  Abonne: {subscriber}\n"
                f"\n  Ajoutez --confirm pour ajouter reellement."
            )
        return svc.group_add_subscriber(group_id, subscriber)

    # --- Campaigns ---

    elif command == "campaigns.list":
        status = _parse_flag(args, "status") or None
        limit = int(_parse_flag(args, "limit") or "25")
        return svc.campaigns_list(status, limit)

    elif command == "campaign.get":
        if not args:
            return format_error("Usage: nm mailerlite campaign get <campaign_id>")
        return svc.campaign_get(args[0])

    # --- Automations ---

    elif command == "automations.list":
        return svc.automations_list()

    elif command == "automation.get":
        if not args:
            return format_error("Usage: nm mailerlite automation get <automation_id>")
        return svc.automation_get(args[0])

    # --- Segments ---

    elif command == "segments.list":
        return svc.segments_list()

    # --- Forms ---

    elif command == "forms.list":
        form_type = _parse_flag(args, "type") or "popup"
        return svc.forms_list(form_type)

    # --- Fields ---

    elif command == "fields.list":
        return svc.fields_list()

    else:
        return format_error(f"Commande MailerLite inconnue: {command}")
