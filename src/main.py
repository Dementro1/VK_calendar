from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.core.config import settings
from src.db.database import engine, Base
from src.scheduler.setup import init_scheduler
from src.api.routes.users import router as users_router
from src.api.routes.auth import router as auth_router
from src.api.routes.settings import router as settings_router

from src.core.loggin_congig import setup_logging
setup_logging()

# Создание таблиц при старте (для учебного проекта, без Alembic)
def create_tables():
    Base.metadata.create_all(bind=engine)

scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    create_tables()
    scheduler = init_scheduler()

    # Синхронизация раз в 5 минут
    from src.scheduler.tasks import sync_all_users
    scheduler.add_job(
        sync_all_users,
        trigger='interval',
        minutes=5,
        id='sync_all_users',
        replace_existing=True
    )
    yield
    if scheduler:
        scheduler.shutdown()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(settings_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}