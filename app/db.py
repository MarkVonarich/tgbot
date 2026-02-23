from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path('/root/resume_radar')
DB_PATH = BASE_DIR / 'data' / 'app.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
