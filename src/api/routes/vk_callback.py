import json
import logging
from fastapi import APIRouter, Request, HTTPException
from src.core.config import settings
from src.services.snooze_handler import parse_snooze_command, apply_snooze
from src.db.database import SessionLocal
from src.db.models.notification_log import NotificationLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vk", tags=["vk_callback"])

@router.post("/callback")
async def vk_callback(request: Request):
    body = await request.json()
    logger.debug(f"VK callback: {json.dumps(body, ensure_ascii=False)}")

    # VK ожидает возврат строки "ok" для подтверждения, иначе будет повторять запросы
    if body.get('type') == 'confirmation':
        # Код подтверждения сервера (нужно указать в настройках группы)
        return {"response": settings.VK_CONFIRMATION_CODE}

    if body.get('type') == 'message_new':
        try:
            message = body['object']['message']
            user_id_vk = message['from_id']  # VK ID отправителя
            text = message['text']

            # Ищем пользователя по vk_id
            from src.db.models.user import User
            db = SessionLocal()
            user = db.query(User).filter(User.vk_id == user_id_vk).first()
            db.close()
            if not user:
                logger.info(f"Message from unknown user VK:{user_id_vk}")
                return {"response": "ok"}

            # Проверяем, команда ли это
            command = parse_snooze_command(text)
            if command:
                # Находим последнее уведомление пользователя, которое можно отложить
                db = SessionLocal()
                last_notification = db.query(NotificationLog).filter(
                    NotificationLog.user_id == user.id,
                    NotificationLog.status == "sent"
                ).order_by(NotificationLog.created_at.desc()).first()
                db.close()
                if last_notification:
                    result = apply_snooze(user.id, last_notification.id, command)
                    # Отправим подтверждение пользователю (через messages.send)
                    from src.integrations.vk_client import VKClient
                    vk = VKClient()
                    vk.send_message(user_id_vk, result)
                else:
                    from src.integrations.vk_client import VKClient
                    vk = VKClient()
                    vk.send_message(user_id_vk, "Нет активных уведомлений для откладывания.")
            else:
                # Обычное сообщение – игнорируем
                pass
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    return {"response": "ok"}