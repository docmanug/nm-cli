from __future__ import annotations
import os
import re
import requests
from nm.core.output import format_error

UNIPILE_DEFAULT_URL = "https://api23.unipile.com:15390"

# Known accounts for quick resolution
KNOWN_ACCOUNTS = {
    "instagram-ia": "GpP9p7JuTlu5Zz14DafeHw",
    "instagram-drelard": "TGuH5DxfTI2H822pErdp7Q",
    "linkedin": "orPPaCbFRKyVWHHXRqDJQg",
}


class UnipileService:
    def __init__(self, api_key: str, base_url: str | None = None):
        self._base_url = base_url or os.environ.get("UNIPILE_BASE_URL", UNIPILE_DEFAULT_URL)
        self._api_key = api_key
        self._headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        self._linkedin_account_id = None

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = requests.get(
            f"{self._base_url}{path}",
            headers=self._headers,
            params=params,
        )
        if not resp.ok:
            raise RuntimeError(f"Unipile GET {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _post(self, path: str, payload: dict | None = None) -> dict:
        resp = requests.post(
            f"{self._base_url}{path}",
            headers=self._headers,
            json=payload or {},
        )
        if not resp.ok:
            raise RuntimeError(f"Unipile POST {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _delete(self, path: str, params: dict | None = None) -> dict:
        resp = requests.delete(
            f"{self._base_url}{path}",
            headers=self._headers,
            params=params,
        )
        if not resp.ok:
            raise RuntimeError(f"Unipile DELETE {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _resolve_account_id(self, account_id: str | None = None, provider: str = "LINKEDIN") -> str:
        if account_id:
            return account_id
        if provider == "LINKEDIN":
            return self._get_linkedin_account_id()
        # Fallback: first account of the given provider type
        data = self._get("/api/v1/accounts")
        for acc in data.get("items", []):
            if acc.get("type", "").upper() == provider.upper():
                return acc["id"]
        raise RuntimeError(f"Aucun compte {provider} connecte dans Unipile")

    def _get_linkedin_account_id(self) -> str:
        if self._linkedin_account_id:
            return self._linkedin_account_id
        data = self._get("/api/v1/accounts")
        items = data.get("items", [])
        for acc in items:
            if acc.get("type") == "LINKEDIN":
                self._linkedin_account_id = acc["id"]
                return self._linkedin_account_id
        raise RuntimeError("Aucun compte LinkedIn connecte dans Unipile")

    @staticmethod
    def extract_post_id(url: str) -> str:
        """Extract LinkedIn post ID from URL."""
        m = re.search(r"activity-(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"ugcPost:(\d+)", url)
        if m:
            return f"urn:li:ugcPost:{m.group(1)}"
        m = re.search(r"share:(\d+)", url)
        if m:
            return f"urn:li:share:{m.group(1)}"
        raise ValueError(f"Impossible d'extraire le post_id depuis: {url}")

    def accounts_list(self) -> str:
        data = self._get("/api/v1/accounts")
        items = data.get("items", [])
        if not items:
            return "Aucun compte Unipile."
        lines = [f"{len(items)} comptes Unipile :\n"]
        for acc in items:
            status = "OK"
            sources = acc.get("sources", [])
            if sources:
                status = sources[0].get("status", "?")
            lines.append(
                f"  [{acc.get('type', '?')}] {acc.get('name', '?')} "
                f"(ID: {acc.get('id', '?')}) — {status}"
            )
        return "\n".join(lines)

    def post_get(self, post_id: str, account_id: str | None = None) -> str:
        account_id = self._resolve_account_id(account_id)
        data = self._get(f"/api/v1/posts/{post_id}", {"account_id": account_id})

        reactions = data.get("reaction_counter", 0)
        comments = data.get("comment_counter", 0)
        reposts = data.get("repost_counter", 0)
        impressions = data.get("impressions_counter", 0)
        analytics = data.get("analytics", {})

        lines = [
            f"Post {post_id}",
            f"  Texte: {(data.get('text', '') or '')[:100]}...",
            f"  Date: {data.get('date', 'N/A')}",
            f"",
            f"  Compteurs :",
            f"    Reactions: {reactions}",
            f"    Commentaires: {comments}",
            f"    Reposts: {reposts}",
            f"    Impressions: {impressions}",
        ]

        if analytics:
            lines.append(f"")
            lines.append(f"  Analytics detailles :")
            lines.append(f"    Impressions: {analytics.get('impressions', 'N/A')}")
            lines.append(f"    Engagements: {analytics.get('engagements', 'N/A')}")
            lines.append(f"    Engagement rate: {analytics.get('engagement_rate', 'N/A')}%")
            lines.append(f"    Clics: {analytics.get('clicks', 'N/A')}")
            lines.append(f"    CTR: {analytics.get('clickthrough_rate', 'N/A')}%")
            lines.append(f"    Nouveaux followers: {analytics.get('followers_gained_from_this_post', 'N/A')}")

        return "\n".join(lines)

    def post_stats_json(self, post_id: str, account_id: str | None = None) -> dict:
        """Return raw stats as dict — used by stats-update skill to write to Monday."""
        account_id = self._resolve_account_id(account_id)
        data = self._get(f"/api/v1/posts/{post_id}", {"account_id": account_id})
        analytics = data.get("analytics", {})

        return {
            "reaction_counter": data.get("reaction_counter", 0),
            "comment_counter": data.get("comment_counter", 0),
            "repost_counter": data.get("repost_counter", 0),
            "impressions_counter": data.get("impressions_counter", 0),
            "impressions": analytics.get("impressions", data.get("impressions_counter", 0)),
            "engagements": analytics.get("engagements", 0),
            "engagement_rate": analytics.get("engagement_rate", 0),
            "clicks": analytics.get("clicks", 0),
            "clickthrough_rate": analytics.get("clickthrough_rate", 0),
            "followers_gained": analytics.get("followers_gained_from_this_post", 0),
            "text": (data.get("text", "") or "")[:100],
            "date": data.get("date", ""),
        }

    @staticmethod
    def _parse_author(author) -> tuple:
        """Parse author field — can be a string or a dict with name/headline."""
        if isinstance(author, str):
            return author, ""
        if isinstance(author, dict):
            name = author.get("name", "?")
            headline = author.get("headline", "")
            return name, headline
        return "?", ""

    def post_comments(self, post_id: str, limit: int = 20, account_id: str | None = None) -> str:
        account_id = self._resolve_account_id(account_id)
        data = self._get(
            f"/api/v1/posts/{post_id}/comments",
            {"account_id": account_id, "limit": limit},
        )
        items = data.get("items", data) if isinstance(data, dict) else data
        if not items:
            return "Aucun commentaire."
        if isinstance(items, dict):
            items = items.get("items", [])
        lines = [f"{len(items)} commentaires :\n"]
        for c in items:
            # Author can be string or dict; author_details may also exist
            author_raw = c.get("author_details", c.get("author", {}))
            name, headline = self._parse_author(author_raw)
            comment_id = c.get("id", "?")
            text = (c.get("text", "") or "")[:150]
            lines.append(f"  [{comment_id}] {name}" + (f" ({headline})" if headline else ""))
            lines.append(f"    {text}")
        return "\n".join(lines)

    def post_reactions(self, post_id: str, limit: int = 100, account_id: str | None = None) -> str:
        account_id = self._resolve_account_id(account_id)
        data = self._get(
            f"/api/v1/posts/{post_id}/reactions",
            {"account_id": account_id, "limit": limit},
        )
        items = data.get("items", data) if isinstance(data, dict) else data
        if not items:
            return "Aucune reaction."
        if isinstance(items, dict):
            items = items.get("items", [])
        # Count by type
        by_type = {}
        for r in items:
            rtype = r.get("type", r.get("reaction_type", "LIKE"))
            by_type[rtype] = by_type.get(rtype, 0) + 1
        lines = [f"{len(items)} reactions :\n"]
        for rtype, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {rtype}: {count}")
        return "\n".join(lines)

    # --- Write commands ---

    def post_comment(self, post_id: str, text: str, account_id: str | None = None) -> str:
        account_id = self._resolve_account_id(account_id)
        payload = {"account_id": account_id, "text": text}
        data = self._post(f"/api/v1/posts/{post_id}/comments", payload)
        comment_id = data.get("id", data.get("comment_id", "?"))
        return (
            f"Commentaire publie\n"
            f"  Post: {post_id}\n"
            f"  Compte: {account_id}\n"
            f"  Comment ID: {comment_id}\n"
            f"  Texte: {text[:100]}{'...' if len(text) > 100 else ''}"
        )

    def comment_reply(self, post_id: str, comment_id: str, text: str, account_id: str | None = None) -> str:
        account_id = self._resolve_account_id(account_id)
        payload = {
            "account_id": account_id,
            "text": text,
            "in_reply_to": comment_id,
        }
        data = self._post(f"/api/v1/posts/{post_id}/comments", payload)
        reply_id = data.get("id", data.get("comment_id", "?"))
        return (
            f"Reponse publiee\n"
            f"  Post: {post_id}\n"
            f"  En reponse a: {comment_id}\n"
            f"  Compte: {account_id}\n"
            f"  Reply ID: {reply_id}\n"
            f"  Texte: {text[:100]}{'...' if len(text) > 100 else ''}"
        )

    def user_posts(self, limit: int = 20, account_id: str | None = None) -> str:
        account_id = self._resolve_account_id(account_id)
        data = self._get(
            f"/api/v1/users/{account_id}/posts",
            {"account_id": account_id, "limit": limit},
        )
        items = data.get("items", data) if isinstance(data, dict) else data
        if not items:
            return "Aucun post."
        if isinstance(items, dict):
            items = items.get("items", [])
        lines = [f"{len(items)} posts recents :\n"]
        for p in items:
            text = (p.get("text", "") or "")[:80]
            reactions = p.get("reaction_counter", 0)
            comments = p.get("comment_counter", 0)
            impressions = p.get("impressions_counter", 0)
            post_id = p.get("id", p.get("social_id", "?"))
            lines.append(
                f"  [{post_id}] {text}..."
            )
            lines.append(
                f"    {impressions} impr | {reactions} reactions | {comments} comments"
            )
        return "\n".join(lines)


def _parse_flag(args: list, name: str) -> str:
    """Extract --name value from args list."""
    flag = f"--{name}"
    for i, a in enumerate(args):
        if a == flag and i + 1 < len(args):
            return args[i + 1]
    return ""


def _has_flag(args: list, name: str) -> bool:
    """Check if --name is present in args (boolean flag)."""
    return f"--{name}" in args


def _resolve_post_id(raw: str) -> str:
    """If raw looks like a LinkedIn URL, extract the post ID."""
    if "linkedin.com" in raw:
        return UnipileService.extract_post_id(raw)
    return raw


def handle_unipile(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("unipile")
    svc = UnipileService(api_key=creds["api_key"])

    account_id = _parse_flag(args, "account-id") or None

    if command == "accounts.list":
        return svc.accounts_list()

    elif command == "post.get":
        if not args:
            return format_error("Usage: nm unipile post get <post_id_or_url> [--account-id <id>]")
        try:
            post_id = _resolve_post_id(args[0])
        except ValueError as e:
            return format_error(str(e))
        return svc.post_get(post_id, account_id=account_id)

    elif command == "post.stats":
        if not args:
            return format_error("Usage: nm unipile post stats <post_id_or_url> [--account-id <id>]")
        try:
            post_id = _resolve_post_id(args[0])
        except ValueError as e:
            return format_error(str(e))
        import json
        return json.dumps(svc.post_stats_json(post_id, account_id=account_id), indent=2)

    elif command == "post.comments":
        if not args:
            return format_error("Usage: nm unipile post comments <post_id_or_url> [--account-id <id>] [--limit N]")
        try:
            post_id = _resolve_post_id(args[0])
        except ValueError as e:
            return format_error(str(e))
        limit = int(_parse_flag(args, "limit") or "20")
        return svc.post_comments(post_id, limit, account_id=account_id)

    elif command == "post.reactions":
        if not args:
            return format_error("Usage: nm unipile post reactions <post_id_or_url> [--account-id <id>] [--limit N]")
        try:
            post_id = _resolve_post_id(args[0])
        except ValueError as e:
            return format_error(str(e))
        limit = int(_parse_flag(args, "limit") or "100")
        return svc.post_reactions(post_id, limit, account_id=account_id)

    elif command == "posts.list":
        limit = int(_parse_flag(args, "limit") or "20")
        return svc.user_posts(limit, account_id=account_id)

    # --- Write commands (require --confirm) ---

    elif command == "post.comment":
        if not args:
            return format_error(
                "Usage: nm unipile post comment <post_id_or_url> --text \"...\" [--account-id <id>] --confirm"
            )
        try:
            post_id = _resolve_post_id(args[0])
        except ValueError as e:
            return format_error(str(e))
        text = _parse_flag(args, "text")
        if not text:
            return format_error("--text est requis")
        resolved_account = account_id or svc._resolve_account_id(None)
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — commentaire non publie\n"
                f"  Endpoint: POST /api/v1/posts/{post_id}/comments\n"
                f"  Account ID: {resolved_account}\n"
                f"  Post: {post_id}\n"
                f"  Texte: {text[:200]}{'...' if len(text) > 200 else ''}\n"
                f"\n  Ajoutez --confirm pour publier reellement."
            )
        return svc.post_comment(post_id, text, account_id=account_id)

    elif command == "comment.reply":
        comment_id_arg = _parse_flag(args, "comment-id") or (args[0] if args else "")
        post_id_raw = _parse_flag(args, "post-id")
        text = _parse_flag(args, "text")
        if not comment_id_arg or not post_id_raw or not text:
            return format_error(
                "Usage: nm unipile comment reply <comment_id> --post-id <post_id> --text \"...\" "
                "[--account-id <id>] --confirm"
            )
        try:
            post_id = _resolve_post_id(post_id_raw)
        except ValueError as e:
            return format_error(str(e))
        resolved_account = account_id or svc._resolve_account_id(None)
        if not _has_flag(args, "confirm"):
            return (
                f"DRY RUN — reponse non publiee\n"
                f"  Endpoint: POST /api/v1/posts/{post_id}/comments (in_reply_to)\n"
                f"  Account ID: {resolved_account}\n"
                f"  Post: {post_id}\n"
                f"  En reponse a: {comment_id_arg}\n"
                f"  Texte: {text[:200]}{'...' if len(text) > 200 else ''}\n"
                f"\n  Ajoutez --confirm pour publier reellement."
            )
        return svc.comment_reply(post_id, comment_id_arg, text, account_id=account_id)

    elif command in ("post.react", "post.unreact", "comment.react"):
        return format_error(
            "Reactions/likes non disponibles via l'API Unipile.\n"
            "  Endpoints testes (tous 404) :\n"
            "    POST /api/v1/posts/{id}/reactions\n"
            "    POST /api/v1/posts/{id}/react\n"
            "    DELETE /api/v1/posts/{id}/reactions\n"
            "  L'API retourne permissions.can_react dans les objets post,\n"
            "  mais n'expose pas d'endpoint d'ecriture pour les reactions.\n"
            "  Teste le 2026-05-12 sur api23.unipile.com:15390."
        )

    else:
        return format_error(f"Commande Unipile inconnue: {command}")
