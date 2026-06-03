import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

from src.db.database import Base
from src.db.models.user import User
from src.db.models.event import Event
from src.db.models.notification_settings import NotificationSettings
from src.db.models.calendar_connection import CalendarConnection

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

@pytest.fixture
def sample_user(db_session):
    user = User(vk_id=123456, timezone="Europe/Moscow")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def sample_settings(db_session, sample_user):
    settings = NotificationSettings(
        user_id=sample_user.id,
        reminder_intervals=[60, 15, 5],
        silence_start="23:00",
        silence_end="08:00",
        silence_exceptions=["врач", "срочный"],
        grouping_window=120
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return settings

@pytest.fixture
def sample_events(db_session, sample_user):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    events_data = [
        {"title": "Встреча с врачом", "start": now + timedelta(hours=2), "end": now + timedelta(hours=3)},
        {"title": "Срочный созвон", "start": now + timedelta(hours=2, minutes=30), "end": now + timedelta(hours=3, minutes=30)},
        {"title": "Обычная встреча", "start": now + timedelta(hours=5), "end": now + timedelta(hours=6)},
        {"title": "Ещё встреча", "start": now + timedelta(hours=5, minutes=30), "end": now + timedelta(hours=6, minutes=30)},
    ]
    events = []
    for i, data in enumerate(events_data):
        event = Event(
            user_id=sample_user.id,
            calendar_connection_id=1,
            google_event_id=f"gevent_{i}",
            title=data["title"],
            start_time=data["start"],
            end_time=data["end"],
            status="active"
        )
        db_session.add(event)
        events.append(event)
    db_session.commit()
    for e in events:
        db_session.refresh(e)
    return events

@pytest.fixture
def sample_connection(db_session, sample_user):
    conn = CalendarConnection(
        user_id=sample_user.id,
        google_id="123",
        access_token="fake",
        refresh_token_encrypted="enc_fake",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        scope="calendar.readonly"
    )
    db_session.add(conn)
    db_session.commit()
    return conn

@pytest.fixture
def mock_sync_session(db_session):
    """Подменяет SessionLocal в модуле sync на тестовую сессию."""
    engine = db_session.bind
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _make_session():
        return TestSessionLocal()

    with patch('src.services.sync.SessionLocal', side_effect=_make_session):
        yield