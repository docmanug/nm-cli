import pytest
from nm.profile import Profile


@pytest.fixture
def sdr_profile(tmp_path):
    yaml_content = """
name: sdr
description: Test SDR profile
services:
  monday:
    boards: [12345]
    commands:
      - leads.list
      - leads.get
    allowed_statuses:
      - Contacted
      - Won
  nextcall:
    commands:
      - send.whatsapp
    limits:
      whatsapp: 5
    max_message_length: 200
"""
    f = tmp_path / "sdr.yaml"
    f.write_text(yaml_content)
    return Profile(str(f))


@pytest.fixture
def full_profile(tmp_path):
    yaml_content = """
name: full
description: Full access
services: "*"
"""
    f = tmp_path / "full.yaml"
    f.write_text(yaml_content)
    return Profile(str(f))


def test_profile_name(sdr_profile):
    assert sdr_profile.name == "sdr"

def test_check_command_allowed(sdr_profile):
    assert sdr_profile.check_command("monday", "leads.list") is True

def test_check_command_denied(sdr_profile):
    assert sdr_profile.check_command("monday", "boards.delete") is False

def test_check_service_denied(sdr_profile):
    assert sdr_profile.check_command("stripe", "customers.list") is False

def test_full_profile_allows_everything(full_profile):
    assert full_profile.check_command("monday", "leads.list") is True
    assert full_profile.check_command("stripe", "customers.list") is True
    assert full_profile.check_command("anything", "any.command") is True

def test_get_service_config(sdr_profile):
    config = sdr_profile.get_service_config("monday")
    assert config["boards"] == [12345]
    assert "leads.list" in config["commands"]

def test_get_service_config_missing(sdr_profile):
    assert sdr_profile.get_service_config("stripe") is None

def test_get_limit(sdr_profile):
    assert sdr_profile.get_limit("nextcall", "whatsapp") == 5

def test_get_limit_no_limit(sdr_profile):
    assert sdr_profile.get_limit("monday", "updates") is None

def test_full_profile_no_limits(full_profile):
    assert full_profile.get_limit("nextcall", "whatsapp") is None

def test_check_board_allowed(sdr_profile):
    assert sdr_profile.check_resource("monday", "boards", 12345) is True

def test_check_board_denied(sdr_profile):
    assert sdr_profile.check_resource("monday", "boards", 99999) is False

def test_full_profile_any_board(full_profile):
    assert full_profile.check_resource("monday", "boards", 99999) is True
