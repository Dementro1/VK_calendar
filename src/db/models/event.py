from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    calendar_connection_id = Column(Integer, ForeignKey("calendar_connections.id"), nullable=False)

    # Внешний идентификатор события в Google Calendar
    google_event_id = Column(String, nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)

    # Время начала и окончания с часовым поясом
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    # Статус события: active, cancelled, modified
    status = Column(String, default="active", nullable=False)

    # Время последней синхронизации этого события
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now())

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="events")
    calendar_connection = relationship("CalendarConnection", backref="events")