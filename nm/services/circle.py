from __future__ import annotations
import requests
from nm.core.output import format_error

CIRCLE_API_URL = "https://app.circle.so/api/v1"


class CircleService:
    def __init__(self, api_token: str, community_id: str = ""):
        self._token = api_token
        self._community_id = community_id
        self._headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        all_params = params or {}
        if self._community_id:
            all_params["community_id"] = self._community_id
        resp = requests.get(
            f"{CIRCLE_API_URL}{path}",
            headers=self._headers,
            params=all_params,
        )
        resp.raise_for_status()
        return resp.json()

    def _detect_community_id(self):
        """Auto-detect community ID from first community."""
        if self._community_id:
            return
        resp = requests.get(
            f"{CIRCLE_API_URL}/communities",
            headers=self._headers,
        )
        resp.raise_for_status()
        communities = resp.json()
        if communities:
            self._community_id = str(communities[0].get("id", ""))

    def spaces_list(self) -> str:
        self._detect_community_id()
        data = self._get("/spaces")
        spaces = data if isinstance(data, list) else data.get("records", data.get("spaces", []))
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
        self._detect_community_id()
        params = {"per_page": limit}
        if space_id and space_id != "all":
            params["space_id"] = space_id
        data = self._get("/posts", params)
        posts = data if isinstance(data, list) else data.get("records", data.get("posts", []))
        if no_reply:
            posts = [p for p in posts if p.get("comments_count", 0) == 0]
        if not posts:
            return "Aucun post" + (" sans reponse" if no_reply else "") + "."
        lines = [f"{len(posts)} posts" + (" sans reponse" if no_reply else "") + " :\n"]
        for p in posts:
            author = p.get("user_name", p.get("user", {}).get("name", "?"))
            comments = p.get("comments_count", 0)
            likes = p.get("likes_count", p.get("reactions_count", 0))
            title = p.get("name", p.get("title", "Sans titre"))
            space = p.get("space_name", p.get("space", {}).get("name", "?"))
            lines.append(
                f"  [{p.get('id', '?')}] {title} — par {author} "
                f"| {comments} commentaires, {likes} likes | Espace: {space}"
            )
        return "\n".join(lines)

    def members_list(self, recent_days: int = 0, limit: int = 20) -> str:
        self._detect_community_id()
        params = {"per_page": limit, "sort": "latest"}
        data = self._get("/community_members", params)
        members = data if isinstance(data, list) else data.get("records", data.get("members", []))
        if recent_days > 0:
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=recent_days)
            filtered = []
            for m in members:
                joined = m.get("created_at", "")
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
        lines = [f"{len(members)} membres" + (f" (derniers {recent_days}j)" if recent_days else "") + " :\n"]
        for m in members:
            name = m.get("name", m.get("first_name", "?"))
            email = m.get("email", "")
            joined = m.get("created_at", "?")[:10] if m.get("created_at") else "?"
            lines.append(f"  {name} | {email} | Rejoint: {joined}")
        return "\n".join(lines)

    def stats(self, period_days: int = 7) -> str:
        self._detect_community_id()
        # Aggregate from posts and members
        posts_data = self._get("/posts", {"per_page": 100})
        posts = posts_data if isinstance(posts_data, list) else posts_data.get("records", [])
        members_data = self._get("/community_members", {"per_page": 100, "sort": "latest"})
        members = members_data if isinstance(members_data, list) else members_data.get("records", [])

        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=period_days)

        recent_posts = 0
        total_comments = 0
        total_likes = 0
        for p in posts:
            created = p.get("created_at", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if dt.replace(tzinfo=None) >= cutoff:
                        recent_posts += 1
                        total_comments += p.get("comments_count", 0)
                        total_likes += p.get("likes_count", p.get("reactions_count", 0))
                except (ValueError, TypeError):
                    pass

        new_members = 0
        for m in members:
            joined = m.get("created_at", "")
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
            f"  Membres totaux: {len(members)}+",
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
