import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from src.services.sync import sync_events_for_user
from src.db.models.event import Event

# Фикстура mock_sync_session теперь в conftest.py, она будет использоваться автоматически через usefixtures
@pytest.mark.usefixtures("mock_sync_session")
class TestSync:
    @patch('src.services.sync.fetch_events')
    @patch('src.scheduler.job_functions.schedule_event_reminders')
    def test_sync_new_event(self, mock_schedule, mock_fetch, db_session, sample_user, sample_connection):
        mock_fetch.return_value = [
            {
                'id': 'test123',
                'summary': 'Test Event',
                'description': 'desc',
                'location': '',
                'start': {'dateTime': '2025-07-01T10:00:00+03:00', 'timeZone': 'Europe/Moscow'},
                'end': {'dateTime': '2025-07-01T11:00:00+03:00', 'timeZone': 'Europe/Moscow'}
            }
        ]
        mock_schedule.return_value = None

        sync_events_for_user(sample_user.id)

        events = db_session.query(Event).filter(Event.user_id == sample_user.id).all()
        assert len(events) == 1
        assert events[0].title == "Test Event"
        assert events[0].google_event_id == "test123"
        assert mock_schedule.called

    @patch('src.services.sync.fetch_events')
    @patch('src.scheduler.job_functions.reschedule_event_reminders')
    @patch('src.scheduler.job_functions.schedule_event_reminders')
    def test_sync_updated_event(self, mock_schedule, mock_reschedule, mock_fetch, db_session, sample_user, sample_connection):
        existing = Event(
            user_id=sample_user.id,
            calendar_connection_id=sample_connection.id,
            google_event_id="test123",
            title="Old Title",
            start_time=datetime(2025, 7, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 7, 1, 10, 0, tzinfo=timezone.utc),
            status="active"
        )
        db_session.add(existing)
        db_session.commit()

        mock_fetch.return_value = [
            {
                'id': 'test123',
                'summary': 'New Title',
                'start': {'dateTime': '2025-07-01T10:00:00+03:00', 'timeZone': 'Europe/Moscow'},
                'end': {'dateTime': '2025-07-01T11:00:00+03:00', 'timeZone': 'Europe/Moscow'}
            }
        ]
        sync_events_for_user(sample_user.id)
        updated = db_session.query(Event).filter(Event.google_event_id == "test123").first()
        assert updated.title == "New Title"
        mock_reschedule.assert_called_once()