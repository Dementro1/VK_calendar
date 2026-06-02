from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from src.db.database import Base

class SnoozeRecord(Base):
    __tablename__ = "snooze_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    original_notification_id = Column(Integer, ForeignKey("notification_logs.id"), nullable=True)

    command = Column(String, nullable=False)                          # "+10", "+1ч", "завтра", "отмена"
    new_remind_time = Column(DateTime(timezone=True), nullable=True)  # новое время, если применимо
    status = Column(String, default="active")                         # active, applied, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())