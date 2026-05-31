from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.db.database import Base

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Базовые интервалы напоминаний в минутах (по умолчанию 60, 15, 5)
    reminder_intervals = Column(JSON, default=[60, 15, 5])

    # Настройки режима тишины
    silence_start = Column(String, nullable=True)  # например "23:00"
    silence_end = Column(String, nullable=True)    # например "08:00"
    silence_exceptions = Column(JSON, default=[])  # ключевые слова

    # Окно группировки в минутах
    grouping_window = Column(Integer, default=120)

    user = relationship("User", backref="notification_settings")