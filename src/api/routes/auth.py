import sys
import os
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.db.database import SessionLocal
from src.db import User
from src.db.models.calendar_connection import CalendarConnection
from src.core.encryption import token_encryption
from src.integrations.google_oauth import get_authorization_url, exchange_code
from src.core.config import settings
from src.db.models.notification_settings import NotificationSettings

router = APIRouter(prefix="/auth", tags=["auth"])

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Схемы запросов/ответов ---
class RegisterRequest(BaseModel):
    vk_id: int

class RegisterResponse(BaseModel):
    user_id: int
    message: str

# --- Эндпоинты ---
@router.post("/register", response_model=RegisterResponse)
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    # Проверка, существует ли уже такой vk_id
    user = db.query(User).filter(User.vk_id == req.vk_id).first()
    if user:
        raise HTTPException(status_code=400, detail="Пользователь с таким ID уже существует")
    # Создание нового пользователя
    user = User(vk_id=req.vk_id)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Создание настроек уведомлений по умолчанию
    default_settings = NotificationSettings(user_id=user.id)
    db.add(default_settings)
    db.commit()
    return RegisterResponse(user_id=user.id, message="Пользователь успешно зарегистрирован")


@router.get("/google/login")
def google_login(user_id: int = Query(..., description="ID зарегистрированного пользователя")):
    # Проверка, что пользователь существует
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Генерация state, содержащий user_id
    state = str(user_id)
    auth_url, _ = get_authorization_url(state=state)
    return {"auth_url": auth_url}


@router.get("/google/callback")
def google_callback(code: str = Query(...), state: str = Query(...)):
    # Извлечение user_id из state
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверные параметры")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Code на токены
        credentials = exchange_code(code)

        # google_id из id_token
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        # Проверка id_token и получение информацию о пользователе Google
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        google_id = id_info.get('sub')  # уникальный идентификатор Google-аккаунта
        email = id_info.get('email')

        if not google_id:
            raise HTTPException(status_code=400, detail="Невозможно получить Google ID")

        # Шифрование refresh_token
        refresh_token = credentials.refresh_token
        encrypted_refresh = token_encryption.encrypt(refresh_token) if refresh_token else None

        # Сохранение или обновление подключения
        conn = db.query(CalendarConnection).filter(CalendarConnection.user_id == user.id).first()
        if conn:
            conn.google_id = google_id
            conn.access_token = credentials.token
            conn.refresh_token_encrypted = encrypted_refresh
            conn.token_expiry = credentials.expiry
            conn.scope = " ".join(credentials.scopes)
        else:
            conn = CalendarConnection(
                user_id=user.id,
                google_id=google_id,
                access_token=credentials.token,
                refresh_token_encrypted=encrypted_refresh,
                token_expiry=credentials.expiry,
                scope=" ".join(credentials.scopes),
            )
            db.add(conn)

        # Если email ещё не сохранён у пользователя
        if email and not user.email:
            user.email = email

        db.commit()

        return {"message": "Успешное соединение с календарем"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()