from __future__ import annotations
import requests
from nm.core.output import format_error

CIRCLE_ADMIN_URL = "https://app.circle.so/api/admin/v2"
CIRCLE_HEADLESS_URL = "https://app.circle.so/api/headless/v1"


class CircleService:
    def __init__(self, api_token: str, community_id: str = ""):
        self._token = api_token
        self._community_id = community_id
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None,
             base: str = CIRCLE_ADMIN_URL) -> dict | list:
        resp = requests.get(
            f"{base}{path}",
            headers=self._headers,
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict,
              base: str = CIRCLE_HEADLESS_URL) -> dict:
        resp = requests.post(
            f"{base}{path}",
            headers=self._headers,
            json=data,
        )
        resp.raise_for_status()
        return resp.json()

    def spaces_list(self) -> str:
        data = self._get("/spaces")
        spaces = data if isinstance(data, list) else data.get("records", data.get("spaces", data.get("data", [])))
        if not spaces:
            return "Aucun espace Circle."
        lines = [f"{len(spaces)} espaces :\n"]
        for s in spaces:
            members = s.get("members_count", s.get("member_count", "?"))
            lines.append(
                f"  [{s.get('id', '?')}] {s.get('name', '?')} — {members} membres"
            )
        return "\n".join(lines)

    def posts_list(self, space_id: str = "", limit: int = 20,
                   no_reply: bool = False) -> str:
        params = {"per_page": limit, "status": "published"}
        if space_id and space_id != "all":
            params["space_id"] = space_id
        data = self._get("/posts", params)
        posts = data if isinstance(data, list) else data.get("records", data.get("posts", data.get("data", [])))
        if no_reply:
            posts = [p for p in posts if p.get("comments_count", p.get("comment_count", 0)) == 0]
        if not posts:
            return "Aucun post" + (" sans reponse" if no_reply else "") + "."
        lines = [f"{len(posts)} posts" + (" sans reponse" if no_reply else "") + " :\n"]
        for p in posts:
            author = p.get("user_name", "")
            if not author:
                user = p.get("user", p.get("author", {}))
                if isinstance(user, dict):
                    author = user.get("name", user.get("first_name", "?"))
            comments = p.get("comments_count", p.get("comment_count", 0))
            likes = p.get("likes_count", p.get("reactions_count", 0))
            title = p.get("name", p.get("title", "Sans titre"))
            space = p.get("space_name", "")
            if not space:
                sp = p.get("space", {})
                if isinstance(sp, dict):
                    space = sp.get("name", "?")
            lines.append(
                f"  [{p.get('id', '?')}] {title} — par {author} "
                f"| {comments} commentaires, {likes} likes | Espace: {space}"
            )
        return "\n".join(lines)

    def members_list(self, recent_days: int = 0, limit: int = 20) -> str:
        body = {
            "per_page": limit,
            "order": "latest",
            "status": "active",
        }
        data = self._post("/search/community_members", body)
        members = data.get("data", [])
        total = data.get("total_count", len(members))

        if recent_days > 0:
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=recent_days)
            filtered = []
            for m in members:
                joined = m.get("created_at", m.get("joined_at", ""))
                if joined:
                    try:
                        dt = datetime.fromisoformat(joined.replace("Z", "+00:00"))
                        if dt.replace(tzinfo=None) >= cutoff:
                            filtered.append(m)
                    except (ValueError, TypeError):
                        pass
            members = filtered

        if not members:
            return f"Aucun nouveau membre" + (f" (derniers {recent_days}j)" if recent_days else "") + "."
        lines = [f"{len(members)} membres" + (f" (derniers {recent_days}j)" if recent_days else f" (total: {total})") + " :\n"]
        for m in members:
            name = m.get("name", m.get("first_name", "?"))
            email = m.get("email", "")
            joined = (m.get("created_at", m.get("joined_at", "")) or "")[:10]
            lines.append(f"  {name} | {email} | Rejoint: {joined}")
        return "\n".join(lines)

    def stats(self, period_days: int = 7) -> str:
        # Get recent posts
        params = {"per_page": 100, "status": "published"}
        data = self._get("/posts", params)
        posts = data if isinstance(data, list) else data.get("records", data.get("data", []))

        # Get recent members
        body = {"per_page": 100, "order": "latest", "status": "active"}
        members_data = self._post("/search/community_members", body)
        members = members_data.get("data", [])
        total_members = members_data.get("total_count", len(members))

        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=period_days)

        recent_posts = 0
        total_comments = 0
        total_likes = 0
        for p in posts:
            created = p.get("created_at", p.get("published_at", ""))
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if dt.replace(tzinfo=None) >= cutoff:
                        recent_posts += 1
                        total_comments += p.get("comments_count", p.get("comment_count", 0))
                        total_likes += p.get("likes_count", p.get("reactions_count", 0))
                except (ValueError, TypeError):
                    pass

        new_members = 0
        for m in members:
            joined = m.get("created_at", m.get("joined_at", ""))
            if joined:
                try:
                    dt = datetime.fromisoformat(joined.replace("Z", "+00:00"))
                    if dt.replace(tzinfo=None) >= cutoff:
                        new_members += 1
                except (ValueError, TypeError):
                    pass

        lines = [
            f"Stats Circle ({period_days}j) :",
            f"  Posts: {recent_posts}",
            f"  Commentaires: {total_comments}",
            f"  Likes/reactions: {total_likes}",
            f"  Nouveaux membres: {new_members}",
            f"  Membres totaux: {total_members}",
        ]
        return "\n".join(lines)


def handle_circle(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("circle")
    config = profile.get_service_config("circle") or {}
    svc = CircleService(
        api_token=creds["api_token"],
        community_id=config.get("community_id", ""),
    )

    def _flag(name):
        for i, a in enumerate(args):
            if a == f"--{name}" and i + 1 < len(args):
                return args[i + 1]
        return ""

    if command == "spaces.list":
        return svc.spaces_list()

    elif command == "posts.list":
        space_id = _flag("space") or "all"
        limit = int(_flag("limit") or "20")
        no_reply = "--no-reply" in args
        return svc.posts_list(space_id, limit, no_reply)

    elif command == "members.list":
        recent = _flag("recent")
        recent_days = 0
        if recent:
            recent_days = int(recent.replace("d", ""))
        limit = int(_flag("limit") or "20")
        return svc.members_list(recent_days, limit)

    elif command == "stats":
        period = _flag("period")
        period_days = 7
        if period:
            period_days = int(period.replace("d", ""))
        return svc.stats(period_days)

    else:
        return format_error(f"Commande Circle inconnue: {command}")
