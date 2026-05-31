from datetime import datetime, timedelta, timezone
from typing import List, Optional

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from src.core.config import settings
from src.core.encryption import token_encryption
from src.db.database import SessionLocal
from src.db.models.calendar_connection import CalendarConnection

def get_credentials_for_user(user_id: int) -> Optional[Credentials]:
    db = SessionLocal()
    try:
        conn = db.query(CalendarConnection).filter(CalendarConnection.user_id == user_id).first()
        if not conn:
            return None

        # Расшифровка refresh-токена
        refresh_token = token_encryption.decrypt(conn.refresh_token_encrypted) if conn.refresh_token_encrypted else None

        credentials = Credentials(
            token=conn.access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=conn.scope.split() if conn.scope else []
        )

        # Если токен истёк, обновить его
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

            # Сохранение нового access-токена и времени истечения в БД
            conn.access_token = credentials.token
            conn.token_expiry = credentials.expiry
            db.commit()

        return credentials

    except Exception as e:
        # Логирование ошибки
        return None
    finally:
        db.close()

#Получение событий из календаря пользователя за указанный период.
def fetch_events(user_id: int, time_min: Optional[datetime] = None, time_max: Optional[datetime] = None) -> List[dict]:
    credentials = get_credentials_for_user(user_id)
    if not credentials:
        return []

    service = build("calendar", "v3", credentials=credentials)

    # Установка границ поиска по умолчанию: от текущего момента до +7 дней
    now = datetime.now(timezone.utc)
    if time_min is None:
        time_min = now
    if time_max is None:
        time_max = now + timedelta(days=7)

    time_min_str = time_min.isoformat()
    time_max_str = time_max.isoformat()

    events_result = []
    page_token = None
    while True:
        events_page = service.events().list(
            calendarId='primary',
            timeMin=time_min_str,
            timeMax=time_max_str,
            singleEvents=True,
            orderBy='startTime',
            pageToken=page_token
        ).execute()

        for event in events_page.get('items', []):
            events_result.append(event)

        page_token = events_page.get('nextPageToken')
        if not page_token:
            break

    return events_result