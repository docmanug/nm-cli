from __future__ import annotations
import re
import requests
from nm.core.output import format_error

UNIPILE_BASE_URL = "https://api1.unipile.com:13111"


class UnipileService:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }
        self._linkedin_account_id = None

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = requests.get(
            f"{UNIPILE_BASE_URL}{path}",
            headers=self._headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

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

    def post_get(self, post_id: str) -> str:
        account_id = self._get_linkedin_account_id()
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

    def post_stats_json(self, post_id: str) -> dict:
        """Return raw stats as dict — used by stats-update skill to write to Monday."""
        account_id = self._get_linkedin_account_id()
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

    def post_comments(self, post_id: str, limit: int = 20) -> str:
        account_id = self._get_linkedin_account_id()
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
            author = c.get("author", {})
            name = author.get("name", "?")
            headline = author.get("headline", "")
            text = (c.get("text", "") or "")[:150]
            lines.append(f"  {name}" + (f" ({headline})" if headline else ""))
            lines.append(f"    {text}")
        return "\n".join(lines)

    def post_reactions(self, post_id: str, limit: int = 100) -> str:
        account_id = self._get_linkedin_account_id()
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

    def user_posts(self, limit: int = 20) -> str:
        account_id = self._get_linkedin_account_id()
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


def handle_unipile(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("unipile")
    svc = UnipileService(api_key=creds["api_key"])

    def _flag(name):
        for i, a in enumerate(args):
            if a == f"--{name}" and i + 1 < len(args):
                return args[i + 1]
        return ""

    if command == "accounts.list":
        return svc.accounts_list()

    elif command == "post.get":
        if not args:
            return format_error("Usage: nm unipile post get <post_id_or_url>")
        post_id = args[0]
        # If it's a URL, extract the post ID
        if "linkedin.com" in post_id:
            try:
                post_id = UnipileService.extract_post_id(post_id)
            except ValueError as e:
                return format_error(str(e))
        return svc.post_get(post_id)

    elif command == "post.stats":
        if not args:
            return format_error("Usage: nm unipile post stats <post_id_or_url>")
        post_id = args[0]
        if "linkedin.com" in post_id:
            try:
                post_id = UnipileService.extract_post_id(post_id)
            except ValueError as e:
                return format_error(str(e))
        import json
        return json.dumps(svc.post_stats_json(post_id), indent=2)

    elif command == "post.comments":
        if not args:
            return format_error("Usage: nm unipile post comments <post_id_or_url>")
        post_id = args[0]
        if "linkedin.com" in post_id:
            try:
                post_id = UnipileService.extract_post_id(post_id)
            except ValueError as e:
                return format_error(str(e))
        limit = int(_flag("limit") or "20")
        return svc.post_comments(post_id, limit)

    elif command == "post.reactions":
        if not args:
            return format_error("Usage: nm unipile post reactions <post_id_or_url>")
        post_id = args[0]
        if "linkedin.com" in post_id:
            try:
                post_id = UnipileService.extract_post_id(post_id)
            except ValueError as e:
                return format_error(str(e))
        limit = int(_flag("limit") or "100")
        return svc.post_reactions(post_id, limit)

    elif command == "posts.list":
        limit = int(_flag("limit") or "20")
        return svc.user_posts(limit)

    else:
        return format_error(f"Commande Unipile inconnue: {command}")
