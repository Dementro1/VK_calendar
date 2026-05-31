import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.db.database import engine, Base


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")

if __name__ == "__main__":
    init_db()