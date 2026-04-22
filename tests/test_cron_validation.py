import pytest
from datetime import datetime
from pydantic import ValidationError
from app.schemas import JobCreate, JobUpdate


class TestJobCreateCronValidation:
    """Test JobCreate cron validation with croniter."""

    def test_valid_cron_expression_passes(self):
        """Valid cron '0 9 * * *' should pass without error."""
        job = JobCreate(
            repo_id=1,
            name="test job",
            entrypoint="python test.py",
            run_mode="cron",
            cron_expression="0 9 * * *",
        )
        assert job.cron_expression == "0 9 * * *"

    def test_valid_cron_with_comma_in_minute_passes(self):
        """Cron with list values like '0,30 * * * *' should pass."""
        job = JobCreate(
            repo_id=1,
            name="test job",
            entrypoint="python test.py",
            run_mode="cron",
            cron_expression="0,30 * * * *",
        )
        assert job.cron_expression == "0,30 * * * *"

    def test_invalid_minute_value_rejected(self):
        """Cron with minute=99 should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                repo_id=1,
                name="test job",
                entrypoint="python test.py",
                run_mode="cron",
                cron_expression="99 9 * * *",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "minute" in str(errors[0]["msg"]).lower() or "99" in str(errors[0]["msg"])

    def test_invalid_hour_value_rejected(self):
        """Cron with hour=99 should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                repo_id=1,
                name="test job",
                entrypoint="python test.py",
                run_mode="cron",
                cron_expression="0 99 * * *",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "hour" in str(errors[0]["msg"]).lower() or "99" in str(errors[0]["msg"])

    def test_cron_mode_requires_expression_still_enforced(self):
        """run_mode='cron' without cron_expression should still raise."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                repo_id=1,
                name="test job",
                entrypoint="python test.py",
                run_mode="cron",
            )
        errors = exc_info.value.errors()
        assert any("cron_expression" in str(e["msg"]) for e in errors)


class TestJobUpdateSchema:
    """Test JobUpdate schema exists with same fields as JobCreate."""

    def test_job_update_exists(self):
        """JobUpdate schema should exist."""
        assert JobUpdate is not None

    def test_job_update_has_same_fields_as_job_create(self):
        """JobUpdate should have all the same fields as JobCreate."""
        job_create_fields = set(JobCreate.model_fields.keys())
        job_update_fields = set(JobUpdate.model_fields.keys())
        # JobUpdate should have all JobCreate fields
        assert job_create_fields.issubset(job_update_fields), (
            f"JobUpdate missing fields: {job_create_fields - job_update_fields}"
        )

    def test_job_update_cron_validation(self):
        """JobUpdate should validate cron expressions too."""
        with pytest.raises(ValidationError):
            JobUpdate(cron_expression="99 9 * * *")

    def test_job_update_cron_requires_expression(self):
        """JobUpdate with run_mode='cron' but no cron_expression should fail."""
        with pytest.raises(ValidationError) as exc_info:
            JobUpdate(repo_id=1, name="test", entrypoint="python test.py", run_mode="cron")
        errors = exc_info.value.errors()
        assert any("cron_expression" in str(e["msg"]) for e in errors)