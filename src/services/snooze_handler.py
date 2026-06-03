import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.db.database import SessionLocal
from src.db.models.event import Event
from src.db.models.notification_log import NotificationLog
from src.db.models.snooze_record import SnoozeRecord
from src.db.models.user import User
from src.scheduler.job_functions import schedule_event_reminders, remove_event_reminders
from src.services.notification_dispatcher import dispatch_notification

logger = logging.getLogger(__name__)

def parse_snooze_command(text: str):
    text = text.strip().lower()
    # Шаблоны команд
    patterns = {
        'отмена': r'^отмена$',
        'завтра': r'^завтра$',
        'минуты': r'^\+(\d+)$',        # +10, +30
        'часы': r'^\+(\d+)ч$',          # +1ч, +5ч
    }
    if re.match(patterns['отмена'], text):
        return {'action': 'cancel'}
    if re.match(patterns['завтра'], text):
        return {'action': 'tomorrow'}
    m = re.match(patterns['минуты'], text)
    if m:
        return {'action': 'minutes', 'value': int(m.group(1))}
    m = re.match(patterns['часы'], text)
    if m:
        return {'action': 'hours', 'value': int(m.group(1))}
    return None

# Применяет команду откладывания к уведомлению
def apply_snooze(user_id: int, notification_log_id: int, command: dict):
    db = SessionLocal()
    try:
        notification = db.query(NotificationLog).filter(NotificationLog.id == notification_log_id).first()
        if not notification or notification.user_id != user_id:
            return "Уведомление не найдено."

        event = None
        if notification.event_id:
            event = db.query(Event).filter(Event.id == notification.event_id).first()
            if not event or event.status == "cancelled":
                return "Событие уже отменено."

        # Создаём запись в snooze_records
        record = SnoozeRecord(
            user_id=user_id,
            event_id=notification.event_id,
            original_notification_id=notification.id,
            command=str(command)
        )

        # Логика применения
        action = command['action']
        if action == 'cancel':
            # Отменить напоминание: удалить все будущие задания для этого события
            if event:
                remove_event_reminders(event)
            notification.status = "cancelled"
            record.status = "applied"
            db.commit()
            return "Напоминание отменено."

        if event is None:
            return "Невозможно отложить: событие не привязано."

        # Определяем новое время напоминания
        now = datetime.now(timezone.utc)
        new_time = None
        if action == 'minutes':
            new_time = now + timedelta(minutes=command['value'])
        elif action == 'hours':
            new_time = now + timedelta(hours=command['value'])
        elif action == 'tomorrow':
            # Завтра в то же время, что и исходное начало события
            original_start = event.start_time
            new_time = original_start + timedelta(days=1)
        else:
            return "Неизвестная команда."

        if new_time <= now:
            return "Указанное время уже прошло."

        # Отмена старых заданий и создание новое одиночное напоминание
        remove_event_reminders(event)
        # Добавляем единственное задание
        from src.scheduler.setup import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            job_id = f"snooze_{event.id}_{int(now.timestamp())}"
            scheduler.add_job(
                send_snooze_notification,
                trigger='date',
                run_date=new_time,
                args=[user_id, event.id, notification.id],
                id=job_id,
                replace_existing=True
            )
        record.new_remind_time = new_time
        record.status = "applied"
        db.add(record)
        db.commit()

        # Подтверждение пользователю
        time_str = new_time.astimezone(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
        return f"Напоминание перенесено на {time_str}."
    except Exception as e:
        logger.error(f"Snooze error: {e}")
        db.rollback()
        return "Произошла ошибка при обработке команды."
    finally:
        db.close()

# Отправляет отложенное уведомление (вызывается планировщиком)
def send_snooze_notification(user_id: int, event_id: int, original_notification_id: int):
    from src.db.models.event import Event
    from src.db.models.user import User
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        if not event or event.status == "cancelled" or not user:
            return
        message = f"Перенесённое напоминание: {event.title}\nНачало: {event.start_time.strftime('%Y-%m-%d %H:%M %Z')}"
        dispatch_notification(
            event_id=event.id,
            user_id=user.id,
            user_vk_id=user.vk_id,
            type="reminder",
            scheduled_for=datetime.now(timezone.utc),
            message=message
        )
    finally:
        db.close()