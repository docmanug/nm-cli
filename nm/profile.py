from __future__ import annotations
import os
import sys
import yaml


class Profile:
    def __init__(self, path: str):
        with open(path) as f:
            data = yaml.safe_load(f)
        self.name = data["name"]
        self.description = data.get("description", "")
        self._services = data.get("services", {})
        self._is_full = self._services == "*"

    @classmethod
    def load(cls) -> Profile:
        profile_name = os.environ.get("NM_PROFILE", "full")
        search_paths = [
            os.path.join(os.environ.get("NM_PROFILES_DIR", ""), f"{profile_name}.yaml"),
            os.path.join(os.path.dirname(__file__), "profiles", f"{profile_name}.yaml"),
            os.path.join(os.getcwd(), "profiles", f"{profile_name}.yaml"),
        ]
        for path in search_paths:
            if os.path.exists(path):
                return cls(path)
        print(f"Error: Profile '{profile_name}' not found", file=sys.stderr)
        sys.exit(1)

    def check_command(self, service: str, command: str) -> bool:
        if self._is_full:
            return True
        svc = self._services.get(service)
        if svc is None:
            return False
        commands = svc.get("commands", [])
        return command in commands

    def get_service_config(self, service: str) -> dict | None:
        if self._is_full:
            return {}
        svc = self._services.get(service)
        return dict(svc) if svc else None

    def get_limit(self, service: str, category: str) -> int | None:
        if self._is_full:
            return None
        svc = self._services.get(service)
        if svc is None:
            return None
        limits = svc.get("limits", {})
        return limits.get(category)

    def check_resource(self, service: str, resource_type: str, resource_id) -> bool:
        if self._is_full:
            return True
        svc = self._services.get(service)
        if svc is None:
            return False
        allowed = svc.get(resource_type, [])
        if not allowed:
            return True
        return resource_id in allowed

    def available_services(self) -> list:
        if self._is_full:
            return ["monday", "nextcall", "elevenlabs", "circle", "blotato",
                    "stripe", "qonto", "meta", "telegram", "n8n", "supabase",
                    "unipile"]
        return list(self._services.keys())

    def available_commands(self, service: str) -> list:
        if self._is_full:
            return []
        svc = self._services.get(service, {})
        return svc.get("commands", [])
