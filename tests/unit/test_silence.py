from datetime import datetime, timezone, time
from src.services.notification_filter import is_silence_active, is_exception_event
from src.db.models.notification_settings import NotificationSettings

class TestSilenceActive:
    def test_silence_not_set(self):
        settings = NotificationSettings(silence_start=None, silence_end=None)
        now = datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc)
        assert not is_silence_active(settings, now)

    def test_inside_silence_over_midnight(self):
        settings = NotificationSettings(silence_start="23:00", silence_end="08:00")
        now = datetime(2025, 1, 1, 2, 0, tzinfo=timezone.utc)
        assert is_silence_active(settings, now)

    def test_outside_silence_over_midnight(self):
        settings = NotificationSettings(silence_start="23:00", silence_end="08:00")
        now = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
        assert not is_silence_active(settings, now)

    def test_inside_silence_same_day(self):
        settings = NotificationSettings(silence_start="01:00", silence_end="05:00")
        now = datetime(2025, 1, 1, 3, 0, tzinfo=timezone.utc)
        assert is_silence_active(settings, now)

def test_is_exception_event():
    exceptions = ["врач", "срочно"]
    assert is_exception_event("Запись к врачу", exceptions)
    assert is_exception_event("Срочно!!!", exceptions)
    assert not is_exception_event("Обычная встреча", exceptions)
    assert is_exception_event("ВРАЧ", exceptions)