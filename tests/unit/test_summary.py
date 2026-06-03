from datetime import datetime, timezone, timedelta
from src.services.weekly_summary import compute_free_windows, generate_weekly_summary
from src.db.models.event import Event

def test_compute_free_windows_no_events():
    now = datetime(2025, 7, 1, 12, 0, tzinfo=timezone.utc)
    end = now + timedelta(days=7)
    windows = compute_free_windows([], now, end)
    assert len(windows) == 1
    assert windows[0] == (now, end)

def test_compute_free_windows_with_events():
    now = datetime(2025, 7, 1, 9, 0, tzinfo=timezone.utc)
    end = now + timedelta(days=1)
    e1 = Event(start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2))
    e2 = Event(start_time=now + timedelta(hours=4), end_time=now + timedelta(hours=5))
    windows = compute_free_windows([e1, e2], now, end)
    # Окна: [now..e1.start) если >1ч? 1 час ровно? По условию >1 часа, значит не войдёт.
    # [e1.end..e2.start) 2 часа -> войдёт.
    # [e2.end..end) >1 часа -> войдёт.
    assert len(windows) == 2
    assert windows[0][0] == e1.end_time
    assert windows[0][1] == e2.start_time
    assert windows[1][0] == e2.end_time
    assert windows[1][1] == end

def test_generate_weekly_summary(db_session, sample_user, sample_events, sample_settings):
    # Добавим события с приоритетными словами
    summary = generate_weekly_summary(sample_user.id, db_session)
    assert "Всего событий: 4" in summary  # sample_events имеет 4 события
    assert "Приоритетные встречи:" in summary
    assert "Встреча с врачом" in summary
    assert "Срочный созвон" in summary
    assert "Свободные окна" in summary