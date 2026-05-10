import pytest
from nm.core.limits import LimitTracker


@pytest.fixture
def tracker(tmp_path):
    db_path = str(tmp_path / "test_limits.sqlite")
    return LimitTracker(db_path)


def test_check_under_limit(tracker):
    assert tracker.check_and_increment("whatsapp", max_limit=5) is True

def test_counter_increments(tracker):
    tracker.check_and_increment("whatsapp", max_limit=5)
    tracker.check_and_increment("whatsapp", max_limit=5)
    assert tracker.get_count("whatsapp") == 2

def test_reject_at_limit(tracker):
    for _ in range(5):
        tracker.check_and_increment("whatsapp", max_limit=5)
    assert tracker.check_and_increment("whatsapp", max_limit=5) is False

def test_different_categories_independent(tracker):
    for _ in range(5):
        tracker.check_and_increment("whatsapp", max_limit=5)
    assert tracker.check_and_increment("sms", max_limit=10) is True

def test_reset_clears_all(tracker):
    tracker.check_and_increment("whatsapp", max_limit=5)
    tracker.check_and_increment("sms", max_limit=10)
    tracker.reset_all()
    assert tracker.get_count("whatsapp") == 0
    assert tracker.get_count("sms") == 0

def test_no_limit_always_passes(tracker):
    for _ in range(100):
        assert tracker.check_and_increment("anything", max_limit=None) is True

def test_status_report(tracker):
    tracker.check_and_increment("whatsapp", max_limit=20)
    tracker.check_and_increment("whatsapp", max_limit=20)
    report = tracker.status_report({"whatsapp": 20, "sms": 10})
    assert "whatsapp: 2/20" in report
    assert "sms: 0/10" in report
