from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from src.db.database import engine

_scheduler_instance = None

def init_scheduler() -> BackgroundScheduler:
    global _scheduler_instance
    jobstores = {
        'default': SQLAlchemyJobStore(engine=engine)
    }
    _scheduler_instance = BackgroundScheduler(jobstores=jobstores, timezone='UTC')
    _scheduler_instance.start()
    return _scheduler_instance

def get_scheduler():
    return _scheduler_instance