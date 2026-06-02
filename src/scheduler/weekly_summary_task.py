import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from src.db.database import SessionLocal
from src.db.models.user import User
from src.db.models.notification_settings import NotificationSettings
from src.services.weekly_summary import generate_weekly_summary
from src.services.notification_dispatcher import dispatch_notification

logger = logging.getLogger(__name__)

def check_weekly_summaries():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        now_utc = datetime.now(timezone.utc)

        for user in users:
            settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user.id).first()
            if not settings:
                continue
            if settings.weekly_summary_day is None or settings.weekly_summary_time is None:
                continue

            # Вычисление желаемого времени отправки в часовом поясе пользователя
            try:
                user_tz = ZoneInfo(user.timezone) if user.timezone else timezone.utc
            except Exception:
                user_tz = timezone.utc

            # Получение время пользователя
            now_user = now_utc.astimezone(user_tz)

            # Формирование запланированного время отправки (ближайший целевой момент)
            target_weekday = settings.weekly_summary_day  # 0-6, где 0=пн
            target_time_str = settings.weekly_summary_time  # "HH:MM"
            try:
                target_hour, target_minute = map(int, target_time_str.split(':'))
            except ValueError:
                continue

            # Вычисление разницы дней до целевого дня недели
            current_weekday = now_user.weekday()  # понедельник=0
            days_ahead = target_weekday - current_weekday
            if days_ahead < 0:
                days_ahead += 7
            # Если сегодня тот же день, но время еще не наступило, days_ahead=0
            if days_ahead == 0:
                scheduled_user_time = now_user.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                if now_user < scheduled_user_time:
                    # Время сегодня еще не пришло, ждать
                    continue
            # scheduled_datetime_user - ближайший целевой момент (в часовом поясе пользователя)
            scheduled_user = now_user.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0) + timedelta(days=days_ahead)
            # Переводим в UTC для сравнения с last_weekly_summary_sent
            scheduled_utc = scheduled_user.astimezone(timezone.utc)

            # Если сводка уже отправлялась после этого момента, пропускаем
            if settings.last_weekly_summary_sent and settings.last_weekly_summary_sent >= scheduled_utc:
                continue

            # Условие отправки: текущее UTC-время >= запланированное UTC
            if now_utc >= scheduled_utc:
                message = generate_weekly_summary(user.id, db)
                dispatch_notification(
                    event_id=None,
                    user_id=user.id,
                    user_vk_id=user.vk_id,
                    type="weekly_summary",
                    scheduled_for=now_utc,
                    message=message
                )
                settings.last_weekly_summary_sent = now_utc
                db.commit()
                logger.info(f"Weekly summary sent to user {user.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error in check_weekly_summaries: {str(e)}")
    finally:
        db.close()