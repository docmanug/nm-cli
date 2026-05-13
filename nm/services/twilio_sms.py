from __future__ import annotations
import requests
from nm.core.output import format_error, format_send_confirmation


class TwilioSmsService:
    """Direct Twilio SMS sending."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self._sid = account_sid
        self._token = auth_token
        self._from = from_number

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Convert 06... to +336..., ensure E.164 format."""
        p = phone.strip().replace(" ", "").replace("-", "")
        if p.startswith("0") and len(p) == 10:
            p = "+33" + p[1:]
        if not p.startswith("+"):
            p = "+" + p
        return p

    def send(self, phone: str, message: str) -> str:
        to = self._normalize_phone(phone)
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Messages.json",
            auth=(self._sid, self._token),
            data={"To": to, "From": self._from, "Body": message},
        )
        if not resp.ok:
            detail = resp.text[:300] if resp.text else ""
            return format_error(f"Twilio SMS {resp.status_code}: {detail}")
        data = resp.json()
        sid = data.get("sid", "?")
        status = data.get("status", "?")
        return format_send_confirmation("SMS", to, f"{status} (sid: {sid})")


def handle_twilio(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("twilio")
    config = profile.get_service_config("twilio") or {}

    svc = TwilioSmsService(
        account_sid=creds["account_sid"],
        auth_token=creds["auth_token"],
        from_number=config.get("from_number", creds.get("from_number", "")),
    )

    def get_flag(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == f"--{flag}" and i + 1 < len(args):
                return args[i + 1]
        return None

    if command == "sms.send":
        if len(args) < 2:
            return format_error('Usage: nm twilio sms send <phone> "message"')
        phone = args[0]
        msg_parts = []
        for a in args[1:]:
            if a.startswith("--"):
                break
            msg_parts.append(a)
        message = " ".join(msg_parts)
        return svc.send(phone, message)

    else:
        return format_error(f"Commande Twilio inconnue: {command}")
