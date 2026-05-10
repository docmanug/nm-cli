import os
import pytest
from click.testing import CliRunner
from nm.cli import main


@pytest.fixture
def runner(tmp_path, monkeypatch):
    profile = tmp_path / "full.yaml"
    profile.write_text("name: full\ndescription: test\nservices: \"*\"\n")
    monkeypatch.setenv("NM_PROFILE", "full")
    monkeypatch.setenv("NM_PROFILES_DIR", str(tmp_path))
    env_file = tmp_path / ".env"
    env_file.write_text("")
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    return CliRunner()


def test_nm_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "nm" in result.output.lower()


def test_nm_no_args_shows_help(runner):
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "monday" in result.output.lower()


def test_nm_unknown_service(runner):
    result = runner.invoke(main, ["fakesvc", "do.thing"])
    assert result.exit_code != 0


@pytest.fixture
def sdr_runner(tmp_path, monkeypatch):
    profile = tmp_path / "sdr.yaml"
    profile.write_text("""
name: sdr
description: test sdr
services:
  monday:
    boards: [12345]
    commands: [leads.list]
  nextcall:
    commands: [contact.get]
  elevenlabs:
    commands: [call.trigger]
""")
    monkeypatch.setenv("NM_PROFILE", "sdr")
    monkeypatch.setenv("NM_PROFILES_DIR", str(tmp_path))
    env_file = tmp_path / ".env"
    env_file.write_text("MONDAY_API_TOKEN=fake\n")
    monkeypatch.setenv("NM_ENV_FILE", str(env_file))
    return CliRunner()


def test_sdr_blocked_service(sdr_runner):
    result = sdr_runner.invoke(main, ["stripe", "customers.list"])
    assert result.exit_code != 0
    assert "non autorise" in result.output.lower() or "not available" in result.output.lower()


def test_sdr_blocked_command(sdr_runner):
    result = sdr_runner.invoke(main, ["monday", "boards", "delete"])
    assert result.exit_code != 0
    assert "non autorisee" in result.output.lower()
