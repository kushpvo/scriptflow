from app.models import Repo, Job, EnvVar, AppSettings
from app.database import init_db


def test_create_repo_and_job(db):
    repo = Repo(name="test", github_url="https://github.com/u/r")
    db.add(repo)
    db.commit()
    db.refresh(repo)
    assert repo.id is not None

    job = Job(repo_id=repo.id, name="j1", entrypoint="main.py", python_version="3.12", run_mode="forever")
    db.add(job)
    db.commit()
    db.refresh(job)
    assert job.repo.name == "test"


def test_env_vars_cascade_delete(db):
    repo = Repo(name="r", github_url="https://github.com/u/r2")
    db.add(repo)
    db.commit()
    job = Job(repo_id=repo.id, name="j", entrypoint="x.py", python_version="3.11", run_mode="cron", cron_expression="0 * * * *")
    db.add(job)
    db.commit()
    ev = EnvVar(job_id=job.id, key="FOO", value="bar")
    db.add(ev)
    db.commit()
    db.delete(job)
    db.commit()
    assert db.query(EnvVar).filter_by(job_id=job.id).count() == 0


def test_app_settings_defaults(db):
    s = AppSettings()
    db.add(s)
    db.commit()
    db.refresh(s)
    assert s.default_python_version == "3.12"
    assert s.log_retention_days == 30
