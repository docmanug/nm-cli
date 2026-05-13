from __future__ import annotations
import os
import sys
from dotenv import dotenv_values

SERVICE_CREDENTIALS = {
    "monday": [
        ("MONDAY_API_TOKEN", "api_token", True),
    ],
    "nextcall": [
        ("NEXTCALL_API_KEY", "api_key", True),
        ("NEXTCALL_API_URL", "api_url", True),
        ("NEXTCALL_USER_ID", "user_id", True),
    ],
    "elevenlabs": [
        ("ELEVENLABS_API_KEY", "api_key", True),
        ("ELEVENLABS_AGENT_ID", "agent_id", True),
        ("ELEVENLABS_PHONE_NUMBER_ID", "phone_number_id", True),
    ],
    "circle": [
        ("CIRCLE_API_TOKEN", "api_token", True),
    ],
    "blotato": [
        ("BLOTATO_API_KEY", "api_key", True),
    ],
    "stripe": [
        ("STRIPE_SECRET_KEY", "secret_key", True),
    ],
    "qonto": [
        ("QONTO_CLIENT_ID", "client_id", True),
        ("QONTO_CLIENT_SECRET", "client_secret", True),
    ],
    "meta": [
        ("META_ACCESS_TOKEN", "access_token", True),
        ("META_AD_ACCOUNT_ID", "ad_account_id", False),
    ],
    "telegram": [
        ("TELEGRAM_BOT_TOKEN", "bot_token", True),
    ],
    "n8n": [
        ("N8N_API_KEY", "api_key", True),
        ("N8N_API_URL", "api_url", True),
    ],
    "gdrive": [
        ("GDRIVE_CLIENT_ID", "client_id", True),
        ("GDRIVE_CLIENT_SECRET", "client_secret", True),
        ("GDRIVE_REFRESH_TOKEN", "refresh_token", True),
    ],
    "heygen": [
        ("HEYGEN_API_KEY", "api_key", True),
    ],
    "unipile": [
        ("UNIPILE_API_KEY", "api_key", True),
    ],
    "supabase": [
        ("SUPABASE_URL", "url", True),
        ("SUPABASE_SERVICE_KEY", "service_key", True),
    ],
    "knowledge": [
        ("OPENAI_API_KEY", "api_key", True),
        ("OPENAI_VECTOR_STORE_ID", "vector_store_id", True),
    ],
    "nextmotion": [
        ("NEXTMOTION_API_URL", "api_url", True),
        ("NEXTMOTION_ACCESS_TOKEN", "access_token", True),
    ],
    "twilio": [
        ("TWILIO_ACCOUNT_SID", "account_sid", True),
        ("TWILIO_AUTH_TOKEN", "auth_token", True),
        ("TWILIO_PHONE_NUMBER", "from_number", False),
    ],
    "evolution": [
        ("EVOLUTION_API_KEY", "api_key", True),
        ("EVOLUTION_API_URL", "api_url", True),
    ],
    "enrich": [
        ("CRAWL4AI_URL", "crawl4ai_url", False),
    ],
    "mailerlite": [
        ("MAILERLITE_API_KEY", "api_key", True),
    ],
}


def _load_env() -> dict:
    env_file = os.environ.get("NM_ENV_FILE", ".env")
    values = dotenv_values(env_file)
    for key in list(values.keys()):
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def get_credentials(service: str) -> dict:
    if service not in SERVICE_CREDENTIALS:
        print(f"Error: Unknown service '{service}'", file=sys.stderr)
        sys.exit(1)

    env = _load_env()
    creds = {}
    missing = []

    for env_var, cred_key, required in SERVICE_CREDENTIALS[service]:
        value = env.get(env_var) or os.environ.get(env_var)
        if value:
            creds[cred_key] = value
        elif required:
            missing.append(env_var)

    if missing:
        print(
            f"Error: Missing credentials for '{service}': {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return creds
