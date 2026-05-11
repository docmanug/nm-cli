from __future__ import annotations
import json
import requests
from nm.core.output import format_error

BLOTATO_API_URL = "https://backend.blotato.com/v2"


class BlotatoService:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._headers = {
            "blotato-api-key": api_key,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = requests.get(
            f"{BLOTATO_API_URL}{path}",
            headers=self._headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        resp = requests.post(
            f"{BLOTATO_API_URL}{path}",
            headers=self._headers,
            json=data,
        )
        resp.raise_for_status()
        return resp.json()

    def accounts_list(self, platform: str = "") -> str:
        params = {}
        if platform:
            params["platform"] = platform
        data = self._get("/users/me/accounts", params)
        items = data.get("items", [])
        if not items:
            return "Aucun compte connecte."
        lines = [f"{len(items)} comptes Blotato :\n"]
        for acc in items:
            lines.append(
                f"  [{acc.get('platform', '?')}] {acc.get('fullname') or acc.get('username', '?')} "
                f"(ID: {acc.get('id', '?')})"
            )
        return "\n".join(lines)

    def post_create(self, account_id: str, platform: str, text: str,
                    media_urls: list[str] | None = None,
                    schedule: str = "") -> str:
        payload = {
            "post": {
                "accountId": account_id,
                "content": {
                    "text": text,
                    "mediaUrls": media_urls or [],
                    "platform": platform,
                },
                "target": {
                    "targetType": platform,
                },
            },
        }
        if schedule:
            payload["scheduledTime"] = schedule
        data = self._post("/posts", payload)
        sub_id = data.get("postSubmissionId", "?")
        mode = f"programme a {schedule}" if schedule else "publie immediatement"
        return f"Post {mode} — ID: {sub_id}"

    def post_status(self, post_id: str) -> str:
        data = self._get(f"/posts/{post_id}")
        lines = [
            f"Post #{post_id}",
            f"  Statut: {data.get('status', 'N/A')}",
        ]
        error = data.get("error")
        if error:
            lines.append(f"  Erreur: {error}")
        return "\n".join(lines)


def handle_blotato(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials
    from nm.core.limits import LimitTracker

    creds = get_credentials("blotato")
    svc = BlotatoService(api_key=creds["api_key"])
    tracker = LimitTracker()

    if command == "accounts.list":
        platform = ""
        for i, a in enumerate(args):
            if a == "--platform" and i + 1 < len(args):
                platform = args[i + 1]
        return svc.accounts_list(platform)

    elif command == "post.create":
        limit = profile.get_limit("blotato", "posts")
        if not tracker.check_and_increment("blotato_posts", limit):
            from nm.core.output import format_limit_hit
            return format_limit_hit("posts", tracker.get_count("blotato_posts"), limit)

        def _flag(name):
            for i, a in enumerate(args):
                if a == f"--{name}" and i + 1 < len(args):
                    return args[i + 1]
            return ""

        account_id = _flag("account")
        platform = _flag("platform")
        text = _flag("text")
        media = _flag("media")
        schedule = _flag("schedule")

        if not account_id or not platform or not text:
            return format_error(
                'Usage: nm blotato post create --account <id> --platform <platform> '
                '--text "contenu" [--media <url>] [--schedule "2026-05-12T09:00:00"]'
            )

        media_urls = [media] if media else []
        return svc.post_create(account_id, platform, text, media_urls, schedule)

    elif command == "post.status":
        if not args:
            return format_error("Usage: nm blotato post status <post_id>")
        return svc.post_status(args[0])

    else:
        return format_error(f"Commande Blotato inconnue: {command}")
