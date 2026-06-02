from datetime import datetime, time, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from src.db.models.event import Event
from src.db.models.notification_settings import NotificationSettings

#Проверка, попадает ли текущее время в интервал тишины
def is_silence_active(settings: NotificationSettings, current_time: datetime) -> bool:
    if not settings.silence_start or not settings.silence_end:
        return False

    try:
        start_h, start_m = map(int, settings.silence_start.split(':'))
        end_h, end_m = map(int, settings.silence_end.split(':'))
        start_time = time(start_h, start_m)
        end_time = time(end_h, end_m)
    except (ValueError, AttributeError):
        return False

    current_time_utc = current_time.astimezone(timezone.utc).time()
    # 23:00 - 08:00 пересекает полночь)
    if start_time < end_time:
        return start_time <= current_time_utc < end_time
    else:
        # Интервал переходит через полночь (23:00-08:00)
        return current_time_utc >= start_time or current_time_utc < end_time

#Проверка, содержит ли название события хотя бы одно ключевое слово из списка исключений.
def is_exception_event(event_title: str, exceptions: List[str]) -> bool:
    title_lower = event_title.lower()
    for word in exceptions:
        if word.lower() in title_lower:
            return True
    return False

#Возвращает список активных событий пользователя от начала определенного события
def get_events_in_group(db: Session, event: Event, grouping_window_minutes: int) -> List[Event]:
    start_range = event.start_time
    end_range = event.start_time + timedelta(minutes=grouping_window_minutes)

    events = db.query(Event).filter(
        Event.user_id == event.user_id,
        Event.status.in_(["active", "modified"]),
        Event.id != event.id,
        Event.start_time >= start_range,
        Event.start_time < end_range
    ).all()

    result = [event] + events
    # Сортировка по времени начала
    result.sort(key=lambda e: e.start_time)
    return result

def compose_group_message(events: List[Event]) -> str:
    lines = ["У вас несколько событий в ближайшее время:"]
    for i, ev in enumerate(events, 1):
        time_str = ev.start_time.strftime('%H:%M')
        lines.append(f"{i}. {time_str} — {ev.title}")
        if ev.location:
            lines[-1] += f" ({ev.location})"
    return "\n".join(lines)