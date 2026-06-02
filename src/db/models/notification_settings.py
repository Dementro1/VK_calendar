from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from src.db.database import Base

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    reminder_intervals = Column(JSON, default=[60, 15, 5])

    silence_start = Column(String, nullable=True)
    silence_end = Column(String, nullable=True)
    silence_exceptions = Column(JSON, default=[])

    grouping_window = Column(Integer, default=120)

    # День недели: 0=понедельник, 6=воскресенье (по умолчанию воскресенье)
    weekly_summary_day = Column(Integer, default=6)
    # Время в формате "HH:MM" (по умолчанию 09:00)
    weekly_summary_time = Column(String, default="09:00")
    # Временная метка последней успешной отправки сводки (UTC)
    last_weekly_summary_sent = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="notification_settings")