from __future__ import annotations
import os
import pytest
from click.testing import CliRunner
from nm.cli import main


@pytest.fixture
def sdr_env(tmp_path, monkeypatch):
    profile = tmp_path / "sdr.yaml"
    profile.write_text("""
name: sdr
description: integration test SDR
services:
  monday:
    boards: [12345]
    commands:
      - leads.list
      - leads.get
      - leads.update
      - leads.note
      - leads.next-actions
    allowed_statuses:
      - Demo booked
      - Contacted
  nextcall:
    commands:
      - contact.get
      - send.whatsapp
      - send.sms
      - calendar.check
    limits:
      whatsapp: 2
      sms: 1
    max_message_length: 100
  elevenlabs:
    commands:
      - call.trigger
      - call.result
      - call.list-today
    limits:
      calls: 1
""")
    monkeypatch.setenv("NM_PROFILE", "sdr")
    monkeypatch.setenv("NM_PROFILES_DIR", str(tmp_path))
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MONDAY_API_TOKEN=fake\n"
        "NEXTCALL_API_KEY=fake\n"
        "NEXTCALL_API_URL=https://fake.example.com\n"
        "NEXTCALL_USER_ID=user1\n"
        "ELEVENLABS_API_KEY=fake\n"
        "ELEVENLABS_AGENT_ID=agent1\n"
    )
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    monkeypatch.setenv("NM_LIMITS_DB", str(tmp_path / "limits.sqlite"))
    return CliRunner()


def test_help_shows_sdr_services(sdr_env):
    result = sdr_env.invoke(main, [])
    assert result.exit_code == 0
    assert "monday" in result.output
    assert "nextcall" in result.output
    assert "elevenlabs" in result.output


def test_blocked_service(sdr_env):
    result = sdr_env.invoke(main, ["stripe", "customers.list"])
    assert result.exit_code != 0
    assert "non autorise" in result.output.lower()


def test_blocked_command(sdr_env):
    result = sdr_env.invoke(main, ["monday", "boards", "delete"])
    assert result.exit_code != 0
    assert "non autorisee" in result.output.lower()


def test_monday_help(sdr_env):
    result = sdr_env.invoke(main, ["monday", "--help"])
    assert result.exit_code == 0
    assert "leads" in result.output
    assert "list" in result.output
