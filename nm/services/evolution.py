from __future__ import annotations
import requests
from nm.core.output import format_error, format_send_confirmation


class EvolutionService:
    """WhatsApp messaging via Evolution API."""

    def __init__(self, api_url: str, api_key: str, instance: str = ""):
        self._base = api_url.rstrip("/")
        self._key = api_key
        self._instance = instance

    def _headers(self) -> dict:
        return {"apikey": self._key, "Content-Type": "application/json"}

    def list_instances(self) -> str:
        resp = requests.get(
            f"{self._base}/instance/fetchInstances",
            headers=self._headers(),
        )
        resp.raise_for_status()
        instances = resp.json()
        if not instances:
            return "Aucune instance Evolution API."
        lines = [f"{len(instances)} instances :\n"]
        for inst in instances:
            name = inst.get("instance", {}).get("instanceName", "?")
            state = inst.get("instance", {}).get("state", "?")
            lines.append(f"  {name} | {state}")
        return "\n".join(lines)

    def send_text(self, phone: str, message: str, instance: str | None = None) -> str:
        inst = instance or self._instance
        if not inst:
            return format_error("Instance Evolution API requise (--instance ou config)")
        # Normalize phone: remove +, ensure country code
        number = phone.replace("+", "").replace(" ", "").replace("-", "")
        resp = requests.post(
            f"{self._base}/message/sendText/{inst}",
            headers=self._headers(),
            json={
                "number": number,
                "text": message,
            },
        )
        if not resp.ok:
            detail = resp.text[:300] if resp.text else ""
            return format_error(f"Evolution API {resp.status_code}: {detail}")
        return format_send_confirmation("WhatsApp", phone, "envoye")


def handle_evolution(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("evolution")
    config = profile.get_service_config("evolution") or {}
    instance = config.get("instance", "")

    svc = EvolutionService(
        api_url=creds["api_url"],
        api_key=creds["api_key"],
        instance=instance,
    )

    def get_flag(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == f"--{flag}" and i + 1 < len(args):
                return args[i + 1]
        return None

    if command == "instances.list":
        return svc.list_instances()

    elif command in ("send", "whatsapp.send"):
        if len(args) < 2:
            return format_error('Usage: nm evolution whatsapp send <phone> "message" [--instance name]')
        phone = args[0]
        msg_parts = []
        for a in args[1:]:
            if a.startswith("--"):
                break
            msg_parts.append(a)
        message = " ".join(msg_parts)
        inst = get_flag("instance")
        return svc.send_text(phone, message, instance=inst)

    else:
        return format_error(f"Commande Evolution inconnue: {command}")
