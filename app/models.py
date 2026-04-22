from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Repo(Base):
    __tablename__ = "repos"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    github_url = Column(String, nullable=False)
    github_token = Column(String, nullable=True)
    auto_pull = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    jobs = relationship("Job", back_populates="repo", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=False)
    name = Column(String, nullable=False)
    entrypoint = Column(String, nullable=False)
    python_version = Column(String, nullable=False, default="3.12")
    run_mode = Column(String, nullable=False, default="forever")  # forever | cron
    cron_expression = Column(String, nullable=True)
    extra_args = Column(String, nullable=True)
    restart_on_crash = Column(Boolean, default=True)
    auto_pull = Column(Boolean, default=False)
    status = Column(String, default="idle")  # idle|running|stopped|crashed|crash-loop|install_failed
    notification_url = Column(String, nullable=True)
    notify_on_stderr = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    repo = relationship("Repo", back_populates="jobs")
    env_vars = relationship("EnvVar", back_populates="job", cascade="all, delete-orphan")


class EnvVar(Base):
    __tablename__ = "env_vars"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False, default="")
    job = relationship("Job", back_populates="env_vars")


class AppSettings(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True, default=1)
    default_python_version = Column(String, default="3.12")
    default_notification_url = Column(String, nullable=True)
    log_retention_days = Column(Integer, default=30)
