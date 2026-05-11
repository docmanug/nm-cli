from __future__ import annotations
import json
import time
import requests
from nm.core.output import format_error

HEYGEN_API_URL = "https://api.heygen.com"


class HeyGenService:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = requests.get(
            f"{HEYGEN_API_URL}{path}",
            headers=self._headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        resp = requests.post(
            f"{HEYGEN_API_URL}{path}",
            headers=self._headers,
            json=data,
        )
        resp.raise_for_status()
        return resp.json()

    def avatars_list(self) -> str:
        data = self._get("/v2/avatars")
        avatars = data.get("data", {}).get("avatars", [])
        photos = data.get("data", {}).get("talking_photos", [])
        lines = [f"{len(avatars)} avatars, {len(photos)} talking photos :\n"]
        lines.append("AVATARS :")
        for a in avatars[:20]:
            lines.append(
                f"  [{a.get('avatar_id', '?')}] {a.get('avatar_name', '?')} "
                f"| {a.get('gender', '?')} | premium: {a.get('premium', False)}"
            )
        if photos:
            lines.append("\nTALKING PHOTOS :")
            for p in photos[:10]:
                lines.append(
                    f"  [{p.get('talking_photo_id', '?')}] {p.get('talking_photo_name', '?')}"
                )
        return "\n".join(lines)

    def voices_list(self, language: str = "fr") -> str:
        data = self._get("/v2/voices")
        voices = data.get("data", {}).get("voices", [])
        if language:
            voices = [v for v in voices if language.lower() in (v.get("language", "").lower())]
        if not voices:
            return f"Aucune voix{' en ' + language if language else ''}."
        lines = [f"{len(voices)} voix" + (f" ({language})" if language else "") + " :\n"]
        for v in voices[:30]:
            emotion = "oui" if v.get("emotion_support") else "non"
            lines.append(
                f"  [{v.get('voice_id', '?')}] {v.get('name', '?')} "
                f"| {v.get('language', '?')} | {v.get('gender', '?')} | emotion: {emotion}"
            )
        return "\n".join(lines)

    def video_generate_v3(self, prompt: str, orientation: str = "portrait",
                          avatar_id: str = "", voice_id: str = "") -> str:
        payload = {
            "prompt": prompt,
            "orientation": orientation,
        }
        if avatar_id:
            payload["avatar_id"] = avatar_id
        if voice_id:
            payload["voice_id"] = voice_id
        data = self._post("/v3/video-agents", payload)
        session_id = data.get("session_id", "?")
        status = data.get("status", "?")
        return f"Video v3 lancee — session: {session_id} | status: {status}"

    def video_generate_v2(self, text: str, avatar_id: str, voice_id: str,
                          title: str = "", width: int = 1080,
                          height: int = 1920, emotion: str = "Friendly",
                          bg_color: str = "#FFFFFF",
                          bg_url: str = "") -> str:
        voice_config = {
            "type": "text",
            "voice_id": voice_id,
            "input_text": text,
            "speed": 1.0,
            "emotion": emotion,
        }
        character_config = {
            "type": "avatar",
            "avatar_id": avatar_id,
            "scale": 1.0,
            "avatar_style": "normal",
        }
        background = {"type": "color", "value": bg_color}
        if bg_url:
            if bg_url.endswith((".mp4", ".webm", ".mov")):
                background = {"type": "video", "url": bg_url, "play_style": "loop", "fit": "cover"}
            else:
                background = {"type": "image", "url": bg_url, "fit": "cover"}

        payload = {
            "title": title or "Anna generated video",
            "video_inputs": [{
                "character": character_config,
                "voice": voice_config,
                "background": background,
            }],
            "dimension": {"width": width, "height": height},
        }
        data = self._post("/v2/video/generate", payload)
        video_id = data.get("data", {}).get("video_id", "?")
        return f"Video v2 lancee — video_id: {video_id} | {width}x{height}"

    def video_status(self, video_id: str) -> str:
        data = self._get("/v1/video_status.get", {"video_id": video_id})
        d = data.get("data", {})
        status = d.get("status", "?")
        lines = [
            f"Video {video_id}",
            f"  Status: {status}",
        ]
        if status == "completed":
            lines.append(f"  URL: {d.get('video_url', 'N/A')}")
            lines.append(f"  Duration: {d.get('duration', '?')}s")
            lines.append(f"  Thumbnail: {d.get('thumbnail_url', 'N/A')}")
        elif status == "failed":
            lines.append(f"  Error: {d.get('error', 'Unknown')}")
        return "\n".join(lines)

    def video_status_json(self, video_id: str) -> dict:
        """Return raw status dict — for programmatic use."""
        data = self._get("/v1/video_status.get", {"video_id": video_id})
        return data.get("data", {})

    def session_status(self, session_id: str) -> str:
        data = self._get(f"/v3/video-agents/{session_id}")
        status = data.get("status", "?")
        lines = [
            f"Session {session_id}",
            f"  Status: {status}",
        ]
        video_id = data.get("video_id")
        if video_id:
            lines.append(f"  Video ID: {video_id}")
            # Get video status too
            vdata = self._get("/v1/video_status.get", {"video_id": video_id})
            vd = vdata.get("data", {})
            lines.append(f"  Video status: {vd.get('status', '?')}")
            if vd.get("status") == "completed":
                lines.append(f"  URL: {vd.get('video_url', 'N/A')}")
                lines.append(f"  Duration: {vd.get('duration', '?')}s")
        return "\n".join(lines)


def handle_heygen(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("heygen")
    svc = HeyGenService(api_key=creds["api_key"])

    def _flag(name):
        for i, a in enumerate(args):
            if a == f"--{name}" and i + 1 < len(args):
                return args[i + 1]
        return ""

    if command == "avatars.list":
        return svc.avatars_list()

    elif command == "voices.list":
        language = _flag("language") or _flag("lang") or "fr"
        return svc.voices_list(language)

    elif command == "video.generate-v3":
        prompt = _flag("prompt")
        if not prompt and args:
            prompt = args[0]
        if not prompt:
            return format_error('Usage: nm heygen video generate-v3 --prompt "..." [--orientation portrait] [--avatar <id>]')
        return svc.video_generate_v3(
            prompt=prompt,
            orientation=_flag("orientation") or "portrait",
            avatar_id=_flag("avatar"),
            voice_id=_flag("voice"),
        )

    elif command == "video.generate-v2":
        text = _flag("text")
        avatar_id = _flag("avatar")
        voice_id = _flag("voice")
        if not text or not avatar_id or not voice_id:
            return format_error('Usage: nm heygen video generate-v2 --text "..." --avatar <id> --voice <id> [--width 1080] [--height 1920]')
        return svc.video_generate_v2(
            text=text,
            avatar_id=avatar_id,
            voice_id=voice_id,
            title=_flag("title"),
            width=int(_flag("width") or "1080"),
            height=int(_flag("height") or "1920"),
            emotion=_flag("emotion") or "Friendly",
            bg_color=_flag("bg-color") or "#FFFFFF",
            bg_url=_flag("bg-url"),
        )

    elif command == "video.status":
        if not args:
            return format_error("Usage: nm heygen video status <video_id>")
        return svc.video_status(args[0])

    elif command == "session.status":
        if not args:
            return format_error("Usage: nm heygen session status <session_id>")
        return svc.session_status(args[0])

    else:
        return format_error(f"Commande HeyGen inconnue: {command}")
