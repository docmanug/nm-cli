from __future__ import annotations
import os
import sys
import click
from nm.profile import Profile
from nm.core.discovery import global_help


def _load_profile() -> Profile:
    profile_name = os.environ.get("NM_PROFILE", "full")
    profiles_dir = os.environ.get(
        "NM_PROFILES_DIR",
        os.path.join(os.path.dirname(__file__), "profiles"),
    )
    path = os.path.join(profiles_dir, f"{profile_name}.yaml")
    if not os.path.exists(path):
        click.echo(f"Error: Profile '{profile_name}' not found at {path}", err=True)
        sys.exit(1)
    return Profile(path)


# Registry of service handlers
SERVICE_REGISTRY = {}


def register_service(name, handler):
    SERVICE_REGISTRY[name] = handler


@click.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True, "help_option_names": []})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def main(ctx, args):
    """nm — CLI agent-native pour l'AIOS"""
    profile = _load_profile()

    if not args or args[0] in ("--help", "-h"):
        click.echo(global_help(profile))
        return

    service_name = args[0]

    # Check service access
    if service_name not in profile.available_services():
        click.echo(f"Error: Service '{service_name}' non autorise pour le profil {profile.name}", err=True)
        sys.exit(1)

    remaining = list(args[1:])

    if not remaining or remaining[0] in ("--help", "-h"):
        from nm.core.discovery import service_help
        click.echo(service_help(service_name, profile))
        return

    # Build dotted command: ["leads", "list"] -> "leads.list"
    command_parts = []
    cmd_args = []
    for i, part in enumerate(remaining):
        if part.startswith("-") or (command_parts and len(command_parts) >= 2):
            cmd_args = remaining[i:]
            break
        command_parts.append(part)
    else:
        cmd_args = []

    command = ".".join(command_parts)

    # Check command permission
    if not profile.check_command(service_name, command):
        click.echo(
            f"Error: Commande '{command}' non autorisee pour le profil {profile.name}",
            err=True,
        )
        sys.exit(1)

    # Dispatch to service handler
    handler = SERVICE_REGISTRY.get(service_name)
    if handler is None:
        click.echo(f"Error: Service '{service_name}' not implemented yet", err=True)
        sys.exit(1)

    try:
        result = handler(command, cmd_args, profile)
        if result:
            click.echo(result)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Register services
from nm.services.monday import handle_monday
register_service("monday", handle_monday)

from nm.services.nextcall import handle_nextcall
register_service("nextcall", handle_nextcall)

from nm.services.elevenlabs import handle_elevenlabs
register_service("elevenlabs", handle_elevenlabs)

from nm.services.blotato import handle_blotato
register_service("blotato", handle_blotato)

from nm.services.circle import handle_circle
register_service("circle", handle_circle)

from nm.services.meta import handle_meta
register_service("meta", handle_meta)

from nm.services.unipile import handle_unipile
register_service("unipile", handle_unipile)
