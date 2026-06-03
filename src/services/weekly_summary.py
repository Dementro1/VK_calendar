from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy.orm import Session

from src.db.models.event import Event
from src.db.models.notification_settings import NotificationSettings
from src.services.notification_filter import is_exception_event

# Создаёт текстовую сводку событий на ближайшие 7 дней
def generate_weekly_summary(user_id: int, db: Session) -> str:
    now = datetime.now(timezone.utc)
    week_end = now + timedelta(days=7)

    # Получить активные события пользователя за этот период
    events = db.query(Event).filter(
        Event.user_id == user_id,
        Event.status.in_(["active", "modified"]),
        Event.start_time >= now,
        Event.start_time < week_end
    ).order_by(Event.start_time).all()

    # Настройки для определения приоритетов
    settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user_id).first()
    exceptions = settings.silence_exceptions if settings else []

    total = len(events)
    priority_events = []
    for ev in events:
        if is_exception_event(ev.title, exceptions):
            priority_events.append(ev)

    # Свободные окна (промежутки > 1 часа между событиями)
    free_windows = compute_free_windows(events, now, week_end)

    # Построение сообщения
    lines = []
    lines.append(f"Еженедельный план на 7 дней ({now.strftime('%d.%m.%Y')} – {week_end.strftime('%d.%m.%Y')})")
    lines.append(f"Всего событий: {total}")
    if priority_events:
        lines.append("Приоритетные встречи:")
        for ev in priority_events:
            time_str = ev.start_time.strftime('%d.%m %H:%M')
            lines.append(f"   • {time_str} — {ev.title}")
    else:
        lines.append("Приоритетных встреч нет.")

    if free_windows:
        lines.append("Свободные окна (более 1 часа):")
        for start, end in free_windows:
            lines.append(f"   • {start.strftime('%d.%m %H:%M')} – {end.strftime('%d.%m %H:%M')}")
    else:
        lines.append("  Нет свободных окон дольше 1 часа.")

    return "\n".join(lines)

# Нахождение промежутков между событиями длительностью более 1 часа
def compute_free_windows(events: List[Event], range_start: datetime, range_end: datetime):
    if not events:
        if (range_end - range_start) > timedelta(hours=1):
            return [(range_start, range_end)]
        return []

    windows = []
    # Нормализация: если дата без зоны – считаем UTC
    def ensure_utc(dt):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    # Проверка окна до первого события
    first_start = ensure_utc(events[0].start_time)
    if (first_start - range_start) > timedelta(hours=1):
        windows.append((range_start, first_start))

    for i in range(len(events) - 1):
        gap_start = ensure_utc(events[i].end_time)
        gap_end = ensure_utc(events[i+1].start_time)
        if (gap_end - gap_start) > timedelta(hours=1):
            windows.append((gap_start, gap_end))

    last_end = ensure_utc(events[-1].end_time)
    if (range_end - last_end) > timedelta(hours=1):
        windows.append((last_end, range_end))

    return windows