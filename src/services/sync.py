import logging
from datetime import datetime, timezone

from src.db.database import SessionLocal
from src.db.models.event import Event
from src.db.models.calendar_connection import CalendarConnection
from src.integrations.google_calendar import fetch_events
from src.scheduler import job_functions
from src.services.conflict_detector import check_and_warn_conflicts

logger = logging.getLogger(__name__)

def sync_events_for_user(user_id: int):
    db = SessionLocal()
    try:
        # Проверка наличия подключения
        conn = db.query(CalendarConnection).filter(CalendarConnection.user_id == user_id).first()
        if not conn:
            logger.warning(f"Sync skipped: no calendar connection for user {user_id}")
            return

        # Получение событий из Google
        google_events = fetch_events(user_id)
        google_event_ids = {e['id'] for e in google_events}

        # Получение всех активных локальных событий пользователя
        local_events = db.query(Event).filter(
            Event.user_id == user_id,
            Event.status.in_(["active", "modified"])
        ).all()
        local_event_map = {e.google_event_id: e for e in local_events}

        now = datetime.now(timezone.utc)

        # Обработка пришедших событий (создание или обновление)
        for gevent in google_events:
            google_id = gevent['id']
            title = gevent.get('summary', 'Без названия')
            description = gevent.get('description', '')
            location = gevent.get('location', '')

            # Извлечение времени начала и конца
            start_str = gevent['start'].get('dateTime', gevent['start'].get('date'))
            end_str = gevent['end'].get('dateTime', gevent['end'].get('date'))

            # Парсинг дат
            start_time = datetime.fromisoformat(start_str)
            end_time = datetime.fromisoformat(end_str)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

            if google_id in local_event_map:
                # Обновление существующего события
                local_event = local_event_map[google_id]
                # Проверка, изменилось ли что-то
                if (local_event.title != title or
                    local_event.description != description or
                    local_event.location != location or
                    local_event.start_time != start_time or
                    local_event.end_time != end_time):
                    # Сохранение старых значений для логики планировщика (отмена старых напоминаний)
                    old_start = local_event.start_time
                    old_end = local_event.end_time
                    # Обновление полей
                    local_event.title = title
                    local_event.description = description
                    local_event.location = location
                    local_event.start_time = start_time
                    local_event.end_time = end_time
                    local_event.status = "modified"
                    local_event.last_synced_at = now
                    # Обновление задач напоминаний: снять старые, поставить новые
                    job_functions.reschedule_event_reminders(local_event, old_start, old_end)
                else:
                    # Без изменений, просто обновить время синхронизации
                    local_event.last_synced_at = now
            else:
                # Создание нового локального события
                new_event = Event(
                    user_id=user_id,
                    calendar_connection_id=conn.id,
                    google_event_id=google_id,
                    title=title,
                    description=description,
                    location=location,
                    start_time=start_time,
                    end_time=end_time,
                    status="active",
                    last_synced_at=now
                )
                db.add(new_event)
                db.flush()  # для получения id
                # Создание задач напоминаний для нового события
                job_functions.schedule_event_reminders(new_event)

        # Обработка событий, удалённых
        for google_id, local_event in local_event_map.items():
            if google_id not in google_event_ids:
                local_event.status = "cancelled"
                local_event.last_synced_at = now
                # Удаление всех запланированных напоминаний для этого события
                job_functions.remove_event_reminders(local_event)

        db.commit()
        check_and_warn_conflicts(user_id, db)
        logger.info(f"Sync completed for user {user_id}: {len(google_events)} events processed.")
    except Exception as e:
        db.rollback()
        logger.error(f"Sync failed for user {user_id}: {str(e)}")
    finally:
        db.close()