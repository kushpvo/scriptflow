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


def _migrate_timezone(engine):
    """Add timezone column to app_settings if it doesn't exist (pre-v0.4)."""
    import sqlalchemy as sa
    with engine.connect() as conn:
        result = conn.execute(sa.text("PRAGMA table_info(app_settings)"))
        cols = [row[1] for row in result]
        if "timezone" not in cols:
            conn.execute(sa.text("ALTER TABLE app_settings ADD COLUMN timezone VARCHAR DEFAULT 'UTC'"))
            conn.execute(sa.text("UPDATE app_settings SET timezone = 'UTC' WHERE timezone IS NULL"))
            conn.commit()


def init_db():
    global engine, SessionLocal
    data_dir = os.environ.get("DATA_DIR", "/data")
    os.makedirs(data_dir, exist_ok=True)
    engine = _make_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    _migrate_timezone(engine)


def get_db():
    if SessionLocal is None:
        raise RuntimeError("init_db() has not been called — database is not initialised")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
