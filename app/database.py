from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os


class Base(DeclarativeBase):
    pass


def _make_engine():
    data_dir = os.environ.get("DATA_DIR", "/data")
    db_path = os.path.join(data_dir, "db.sqlite")
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


# Module-level references; reassigned by init_db() so tests can override DATA_DIR first.
engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal
    data_dir = os.environ.get("DATA_DIR", "/data")
    os.makedirs(data_dir, exist_ok=True)
    engine = _make_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)


def get_db():
    if SessionLocal is None:
        raise RuntimeError("init_db() has not been called — database is not initialised")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
