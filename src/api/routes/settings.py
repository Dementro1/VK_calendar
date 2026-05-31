from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List

from src.db.database import SessionLocal
from src.db.models.user import User
from src.db.models.notification_settings import NotificationSettings

router = APIRouter(prefix="/settings", tags=["settings"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Схемы Pydantic
class SettingsResponse(BaseModel):
    user_id: int
    reminder_intervals: List[int]
    silence_start: str = None
    silence_end: str = None
    silence_exceptions: List[str]
    grouping_window: int

class SettingsUpdate(BaseModel):
    reminder_intervals: List[int] = Field(..., example=[60, 15, 5])
    silence_start: str = None
    silence_end: str = None
    silence_exceptions: List[str] = Field(default=[])
    grouping_window: int = 120

@router.get("/", response_model=SettingsResponse)
def get_settings(user_id: int, db: Session = Depends(get_db)):
    #Получение текущих настроек пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings

@router.put("/", response_model=SettingsResponse)
def update_settings(user_id: int, update: SettingsUpdate, db: Session = Depends(get_db)):
    #Обновление настроек пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user_id).first()
    if not settings:
        # создать, если ещё нет (хотя должно создаваться при регистрации)
        settings = NotificationSettings(user_id=user_id)
        db.add(settings)

    settings.reminder_intervals = update.reminder_intervals
    settings.silence_start = update.silence_start
    settings.silence_end = update.silence_end
    settings.silence_exceptions = update.silence_exceptions
    settings.grouping_window = update.grouping_window
    db.commit()
    db.refresh(settings)
    return settings