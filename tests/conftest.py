import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient
from app.database import Base, get_db, init_db
from app.main import app


@pytest.fixture(scope="session")
def tmp_data_dir():
    """Set DATA_DIR before any fixture or app code reads it.
    Must remain session-scoped so it fires before function-scoped fixtures trigger lifespan."""
    with tempfile.TemporaryDirectory() as d:
        os.environ["DATA_DIR"] = d
        yield d
        del os.environ["DATA_DIR"]


@pytest.fixture
def db(tmp_data_dir):
    init_db()  # Initialize database module state using tmp_data_dir
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
