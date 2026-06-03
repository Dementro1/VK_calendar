import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, after_log

from src.db.database import SessionLocal
from src.db.models.notification_log import NotificationLog
from src.integrations.vk_client import VKClient

logger = logging.getLogger(__name__)

# Создание глобального экземпляря клиента
vk_client = VKClient()

# Функция для записи в лог состояния
def create_notification_log(db: Session, user_id: int, event_id: Optional[int], type: str,
                            scheduled_for: datetime, message_text: str) -> NotificationLog:
    log_entry = NotificationLog(
        user_id=user_id,
        event_id=event_id,
        type=type,
        status="pending",
        scheduled_for=scheduled_for,
        message_text=message_text
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

# Декорированная функция отправки
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    after=after_log(logger, logging.DEBUG)
)
def _send_with_retry(user_vk_id: int, message: str):
    return vk_client.send_message(user_vk_id, message)

def dispatch_notification(event_id: Optional[int], user_id: int, user_vk_id: int, type: str,
                          scheduled_for: datetime, message: str):
    #Полный цикл отправки уведомления: запись в лог, попытка отправки, обновление лога результатом, повторные попытки при сбоях
    db = SessionLocal()
    try:
        # Создание записи в истории
        log_entry = create_notification_log(db, user_id, event_id, type, scheduled_for, message)
        try:
            response = _send_with_retry(user_vk_id, message)
            if "error" in response:
                # Ошибка на уровне VK API
                log_entry.status = "failed"
                log_entry.error_message = response.get("error", "VK error")
                log_entry.retry_count = 3
            else:
                log_entry.status = "sent"
                log_entry.sent_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            # Исключение после 3 попыток
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            log_entry.retry_count = 3
            db.commit()
            logger.error(f"Final failure sending notification {log_entry.id}: {str(e)}")
    finally:
        db.close()