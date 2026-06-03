import logging
from src.db.database import SessionLocal
from src.db.models.user import User
from src.services.sync import sync_events_for_user

logger = logging.getLogger(__name__)

# Проходит по всем активным пользователям и запускает синхронизацию их календарей
def sync_all_users():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            sync_events_for_user(user.id)
    except Exception as e:
        logger.error(f"Global sync error: {str(e)}")
    finally:
        db.close()