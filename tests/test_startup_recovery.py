import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Job, Repo
from app.database import Base


@pytest.fixture
def setup_db(tmp_data_dir):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    connection = engine.connect()
    transaction = connection.begin()
    test_session = sessionmaker(bind=connection)()

    # Override app.database module globals so lifespan() uses our test session
    import app.database as db_mod
    import app.main as main_mod

    # Patch init_db to be a no-op so it doesn't overwrite our SessionLocal
    original_init_db = db_mod.init_db
    db_mod.init_db = lambda: None

    # Set up the test sessionmaker before lifespan runs
    db_mod.engine = engine
    db_mod.SessionLocal = sessionmaker(bind=engine)

    # Override the name binding in app.main's namespace so it also uses our SessionLocal
    main_mod.SessionLocal = db_mod.SessionLocal

    yield test_session

    db_mod.init_db = original_init_db
    test_session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def mock_process_manager():
    with patch("app.main.process_manager") as mock:
        mock.start = AsyncMock()
        yield mock


@pytest.fixture
def mock_scheduler():
    # Nightly rotation is now an asyncio task, no scheduler to mock
    yield


@pytest.mark.asyncio
async def test_restart_on_crash_jobs_recovered(setup_db, mock_process_manager, mock_scheduler):
    repo = Repo(name="r", github_url="https://github.com/u/r")
    setup_db.add(repo)
    setup_db.commit()
    job = Job(
        repo_id=repo.id, name="myjob", entrypoint="main.py",
        python_version="3.12", run_mode="forever",
        status="running", restart_on_crash=True,
    )
    setup_db.add(job)
    setup_db.commit()

    # Simulate lifespan startup
    from app.main import lifespan
    from fastapi import FastAPI

    mock_app = FastAPI()
    async with lifespan(mock_app):
        mock_process_manager.start.assert_called()

    assert mock_process_manager.start.called


@pytest.mark.asyncio
async def test_no_restart_jobs_marked_stopped(setup_db, mock_process_manager, mock_scheduler):
    repo = Repo(name="r2", github_url="https://github.com/u/r2")
    setup_db.add(repo)
    setup_db.commit()
    job = Job(
        repo_id=repo.id, name="norerun", entrypoint="main.py",
        python_version="3.12", run_mode="forever",
        status="running", restart_on_crash=False,
    )
    setup_db.add(job)
    setup_db.commit()

    from app.main import lifespan
    from fastapi import FastAPI

    mock_app = FastAPI()
    async with lifespan(mock_app):
        setup_db.refresh(job)
        assert job.status == "stopped"

    assert not mock_process_manager.start.called
