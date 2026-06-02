import logging
from datetime import datetime, timezone, timedelta
from apscheduler.jobstores.base import JobLookupError

from src.db.database import SessionLocal
from src.db.models.event import Event
from src.db.models.user import User
from src.db.models.notification_settings import NotificationSettings
from src.services.notification_dispatcher import dispatch_notification
from src.services.notification_filter import (
    is_silence_active,
    is_exception_event,
    get_events_in_group,
    compose_group_message,
)

from src.scheduler.setup import get_scheduler
logger = logging.getLogger(__name__)

#Удаляет все запланированные напоминания для списка событий.
def remove_reminders_for_events(event_ids: list):
    scheduler = get_scheduler()
    if not scheduler:
        return
    for job in scheduler.get_jobs():
        # Идентификаторы напоминаний: reminder_{event_id}_{minutes}
        for eid in event_ids:
            if job.id.startswith(f"reminder_{eid}_"):
                try:
                    scheduler.remove_job(job.id)
                    logger.debug(f"Removed job {job.id}")
                except Exception:
                    pass

#Отправка уведомления с учётом режима тишины и группировки
def send_notification(event_id: int):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event or event.status == "cancelled":
            logger.info(f"Notification skipped: event {event_id} not found or cancelled")
            return

        user = db.query(User).filter(User.id == event.user_id).first()
        settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == event.user_id).first()
        if not user or not settings:
            logger.error(f"User or settings missing for event {event_id}")
            return

        now = datetime.now(timezone.utc)

        # ---- Проверка режима тишины ----
        if is_silence_active(settings, now) and not is_exception_event(event.title, settings.silence_exceptions):
            logger.info(f"Suppressed notification for event {event_id} due to silence mode")
            scheduler = get_scheduler()
            if scheduler:
                for job in scheduler.get_jobs():
                    if job.id.startswith(f"reminder_{event.id}_"):
                        try:
                            scheduler.remove_job(job.id)
                        except Exception:
                            pass
            return

        # ---- Проверка группировки ----
        grouping_window = settings.grouping_window
        if grouping_window > 0:
            group = get_events_in_group(db, event, grouping_window)
            if len(group) > 1:
                message = compose_group_message(group)
                dispatch_notification(
                    event_id=None,
                    user_id=user.id,
                    user_vk_id=user.vk_id,
                    type="reminder",
                    scheduled_for=now,
                    message=message
                )
                # Удаляем все напоминания для событий группы (включая текущее)
                remove_reminders_for_events([e.id for e in group])
                logger.info(f"Group notification sent for events: {[e.id for e in group]}")
                return

        # ---- Обычное одиночное уведомление ----
        message = f"Напоминание: {event.title}\nНачало: {event.start_time.strftime('%Y-%m-%d %H:%M %Z')}"
        if event.location:
            message += f"\nМесто: {event.location}"

        dispatch_notification(
            event_id=event.id,
            user_id=user.id,
            user_vk_id=user.vk_id,
            type="reminder",
            scheduled_for=now,
            message=message
        )
    finally:
        db.close()

def schedule_event_reminders(event: Event):
    db = SessionLocal()
    try:
        settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == event.user_id).first()
        intervals = settings.reminder_intervals if settings else [60, 15, 5]
        scheduler = get_scheduler()
        if not scheduler:
            return
        for minutes in intervals:
            remind_time = event.start_time - timedelta(minutes=minutes)
            # Пропустить напоминание, если время уже прошло
            if remind_time < datetime.now(timezone.utc):
                continue
            job_id = f"reminder_{event.id}_{minutes}"
            # Удаление старого задания с таким же ID
            try:
                scheduler.remove_job(job_id)
            except JobLookupError:
                pass
            scheduler.add_job(
                send_notification,
                trigger='date',
                run_date=remind_time,
                args=[event.id],
                id=job_id,
                replace_existing=True
            )
            logger.debug(f"Scheduled reminder {job_id} at {remind_time}")
    finally:
        db.close()

#Обработка изменения времени события: удаление старых напоминаний, создание новых.
def reschedule_event_reminders(event: Event, old_start, old_end):
    remove_event_reminders(event)
    schedule_event_reminders(event)

 #Удаление всех запланированных напоминаний для данного события.
def remove_event_reminders(event: Event):
    scheduler = get_scheduler()
    if not scheduler:
        return
    # Удаление всех job_id, начинающихся с reminder_{event.id}_
    for job in scheduler.get_jobs():
        if job.id.startswith(f"reminder_{event.id}_"):
            try:
                scheduler.remove_job(job.id)
                logger.debug(f"Removed job {job.id}")
            except JobLookupError:
                pass