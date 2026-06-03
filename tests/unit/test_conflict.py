from datetime import datetime, timezone, timedelta
from src.services.conflict_detector import find_conflicts, get_first_conflict_time
from src.db.models.event import Event

def make_event(title, start_h, end_h):
    """Вспомогательная функция создания объекта Event без БД."""
    now = datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc)
    return Event(
        title=title,
        start_time=now + timedelta(hours=start_h),
        end_time=now + timedelta(hours=end_h),
        status="active"
    )

def test_no_conflicts():
    e1 = make_event("A", 9, 10)
    e2 = make_event("B", 10, 11)
    conflicts = find_conflicts([e1, e2])
    assert len(conflicts) == 0

def test_conflict_detected():
    e1 = make_event("A", 9, 11)
    e2 = make_event("B", 10, 12)
    conflicts = find_conflicts([e1, e2])
    assert len(conflicts) == 1
    pair = conflicts[0]
    assert (e1 in pair and e2 in pair)

def test_multiple_conflicts():
    e1 = make_event("A", 9, 12)
    e2 = make_event("B", 10, 13)
    e3 = make_event("C", 11, 14)
    conflicts = find_conflicts([e1, e2, e3])
    # Ожидаем три пары: (e1,e2), (e1,e3), (e2,e3)
    assert len(conflicts) == 3

def test_get_first_conflict_time():
    e1 = make_event("A", 10, 12)
    e2 = make_event("B", 9, 11)  # более раннее начало
    conflicts = [(e1, e2)]
    earliest = get_first_conflict_time(conflicts)
    assert earliest == e2.start_time