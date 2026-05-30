from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.core.config import settings
from src.scheduler.setup import init_scheduler

scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    scheduler = init_scheduler()
    yield
    if scheduler:
        scheduler.shutdown()

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}