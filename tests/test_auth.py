import os
import pytest
from nm.core.auth import get_credentials


def test_get_credentials_returns_configured_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("MONDAY_API_TOKEN=test-token-123\n")
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    creds = get_credentials("monday")
    assert creds["api_token"] == "test-token-123"


def test_get_credentials_missing_key_raises(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    with pytest.raises(SystemExit):
        get_credentials("monday")


def test_get_credentials_nextcall(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "NEXTCALL_API_KEY=nc-key\nNEXTCALL_API_URL=https://example.com\nNEXTCALL_USER_ID=user1\n"
    )
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    creds = get_credentials("nextcall")
    assert creds["api_key"] == "nc-key"
    assert creds["api_url"] == "https://example.com"
    assert creds["user_id"] == "user1"
