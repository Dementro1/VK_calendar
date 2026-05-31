import logging
from datetime import datetime, timezone, timedelta
from apscheduler.jobstores.base import JobLookupError

from src.db.database import SessionLocal
from src.db.models.event import Event
from src.db.models.user import User
from src.db.models.notification_settings import NotificationSettings
from src.services.notification_dispather import dispatch_notification

logger = logging.getLogger(__name__)

#Возвращает глобальный экземпляр планировщика. Будет установлен при инициализации
def get_scheduler():
    from src.main import scheduler
    return scheduler

#Отправка уведомления
def send_notification(event_id: int):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event or event.status == "cancelled":
            logger.info(f"Notification skipped: event {event_id} not found or cancelled")
            return

        # Получение пользователя и его VK ID
        user = db.query(User).filter(User.id == event.user_id).first()
        if not user:
            logger.error(f"User not found for event {event_id}")
            return

        # Формирование текста сообщения
        message = f"Напоминание: {event.title}\nНачало: {event.start_time.strftime('%Y-%m-%d %H:%M %Z')}"
        if event.location:
            message += f"\nМесто: {event.location}"

        # Отправка через диспетчер
        dispatch_notification(
            event_id=event.id,
            user_id=user.id,
            user_vk_id=user.vk_id,
            type="reminder",
            scheduled_for=datetime.now(timezone.utc),  # время, на которое было запланировано
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