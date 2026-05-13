from __future__ import annotations
import subprocess
from nm.core.output import format_error, format_send_confirmation


def handle_email(command: str, args: list, profile) -> str:
    """Send email via himalaya CLI (must be installed on system)."""
    config = profile.get_service_config("email") or {}
    default_account = config.get("account", "gmail")

    def get_flag(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == f"--{flag}" and i + 1 < len(args):
                return args[i + 1]
        return None

    if command == "send" or command.startswith("send."):
        # Handle case where CLI joins "send" + "email@x.com" into "send.email@x.com"
        to = get_flag("to")
        if not to and command.startswith("send."):
            to = command.split(".", 1)[1]
        if not to:
            to = args[0] if args and not args[0].startswith("--") else None
        subject = get_flag("subject") or "Sans objet"
        body = get_flag("body") or ""
        account = get_flag("account") or default_account

        if not to:
            return format_error('Usage: nm email send <to> --subject "..." --body "..."')
        if not body:
            return format_error("--body requis")

        # Build raw email
        raw = f"From: {account}\nTo: {to}\nSubject: {subject}\n\n{body}"

        try:
            result = subprocess.run(
                ["himalaya", "message", "send", "-a", account],
                input=raw,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                # If the error is just about saving to Sent folder, email was still sent
                if "cannot add IMAP message" in stderr or "Folder doesn't exist" in stderr:
                    return format_send_confirmation("Email", to, f"envoye depuis {account} (save Sent skipped)")
                return format_error(f"himalaya error: {stderr[:300]}")
            return format_send_confirmation("Email", to, f"envoye depuis {account}")
        except FileNotFoundError:
            return format_error("himalaya non installe sur ce systeme")
        except subprocess.TimeoutExpired:
            return format_error("himalaya timeout (15s)")

    else:
        return format_error(f"Commande email inconnue: {command}")
