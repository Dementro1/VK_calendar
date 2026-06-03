import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sqlalchemy.orm import Session

from src.db.models.event import Event

logger = logging.getLogger(__name__)

#Нахождение всех пар пересекающихся событий
def find_conflicts(events: List[Event]) -> List[Tuple[Event, Event]]:
    conflicts = []
    n = len(events)
    for i in range(n):
        for j in range(i + 1, n):
            e1 = events[i]
            e2 = events[j]
            # Проверка пересечения: начало одного до конца другого
            if e1.start_time < e2.end_time and e2.start_time < e1.end_time:
                conflicts.append((e1, e2))
    return conflicts

# Возвращает наименьшее время начала среди всех конфликтующих событий
def get_first_conflict_time(conflicts: List[Tuple[Event, Event]]) -> datetime:
    earliest = None
    for e1, e2 in conflicts:
        for ev in (e1, e2):
            if earliest is None or ev.start_time < earliest:
                earliest = ev.start_time
    return earliest

# Планирует отправку предупреждения о конфликте за 1 час до начала первого события
def schedule_conflict_warning(user_id: int, event1: Event, event2: Event):
    from src.scheduler.setup import get_scheduler
    scheduler = get_scheduler()
    if not scheduler:
        return

    # Время предупреждения: за 1 час до самого раннего из двух событий
    conflict_start = min(event1.start_time, event2.start_time)
    warning_time = conflict_start - timedelta(hours=1)
    now = datetime.now(timezone.utc)

    if warning_time <= now:
        # Если предупреждение нужно отправить прямо сейчас или уже прошло
        _send_conflict_message(user_id, event1, event2)
    else:
        job_id = f"conflict_warn_{event1.id}_{event2.id}"
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        scheduler.add_job(
            _send_conflict_message,
            trigger='date',
            run_date=warning_time,
            args=[user_id, event1, event2],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Scheduled conflict warning at {warning_time} for events {event1.id}, {event2.id}")

# Отправка сообщения о конфликте
def _send_conflict_message(user_id: int, event1: Event, event2: Event):
    from src.db.database import SessionLocal
    from src.db.models.user import User
    from src.services.notification_dispatcher import dispatch_notification

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        message = (
            f"Обнаружен конфликт событий:\n"
            f"1. {event1.title} – начало {event1.start_time.strftime('%H:%M')}\n"
            f"2. {event2.title} – начало {event2.start_time.strftime('%H:%M')}\n\n"
            f"Пожалуйста, выберите действие: оставьте как есть или отмените одно из событий."
        )
        dispatch_notification(
            event_id=None,
            user_id=user.id,
            user_vk_id=user.vk_id,
            type="conflict",
            scheduled_for=datetime.now(timezone.utc),
            message=message
        )
    finally:
        db.close()

# Нахождение всех активных конфликтов и планирование предупреждения для первого
def check_and_warn_conflicts(user_id: int, db: Session):
    events = db.query(Event).filter(
        Event.user_id == user_id,
        Event.status.in_(["active", "modified"]),
        Event.conflict_resolved == False
    ).all()

    conflicts = find_conflicts(events)
    if not conflicts:
        return

    first_pair = conflicts[0]
    schedule_conflict_warning(user_id, first_pair[0], first_pair[1])