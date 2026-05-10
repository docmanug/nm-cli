from __future__ import annotations
from nm.profile import Profile


def service_help(service: str, profile: Profile) -> str:
    commands = profile.available_commands(service)
    if not commands:
        return f"Service '{service}' — all commands available (profile: {profile.name})"
    lines = [f"Service '{service}' — profile: {profile.name}", ""]
    lines.append("Commands disponibles:")
    for cmd in sorted(commands):
        lines.append(f"  nm {service} {cmd.replace('.', ' ')}")
    return "\n".join(lines)


def global_help(profile: Profile) -> str:
    services = profile.available_services()
    lines = [f"nm-cli — profil actif: {profile.name}", ""]
    lines.append("Services disponibles:")
    for svc in sorted(services):
        lines.append(f"  nm {svc}")
    lines.append("")
    lines.append("Utilise 'nm <service> --help' pour les commandes disponibles.")
    return "\n".join(lines)
