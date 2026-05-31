from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.db.database import engine

def init_scheduler() -> BackgroundScheduler:
    jobstores = {
        'default': SQLAlchemyJobStore(engine=engine)
    }
    scheduler = BackgroundScheduler(jobstores=jobstores, timezone='UTC')
    scheduler.start()
    return scheduler