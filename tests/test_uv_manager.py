import os
from pathlib import Path

import pytest
from app.uv_manager import create_venv, install_requirements, _venv_path


@pytest.mark.asyncio
async def test_create_venv(tmp_data_dir):
    venv = await create_venv(1, "3.12")
    assert venv.exists()
    assert (venv / "bin" / "python").exists()


@pytest.mark.asyncio
async def test_create_venv_idempotent(tmp_data_dir):
    v1 = await create_venv(2, "3.12")
    v2 = await create_venv(2, "3.12")
    assert v1 == v2


@pytest.mark.asyncio
async def test_create_venv_bad_version(tmp_data_dir):
    with pytest.raises(RuntimeError):
        await create_venv(3, "3.99")


@pytest.mark.asyncio
async def test_install_requirements_missing(tmp_data_dir):
    await create_venv(4, "3.12")
    result = await install_requirements(4, repo_id=4)
    assert result is None


@pytest.mark.asyncio
async def test_install_requirements_success(tmp_data_dir):
    await create_venv(5, "3.12")
    req_path = Path(os.environ["DATA_DIR"]) / "repos" / "5" / "requirements.txt"
    req_path.parent.mkdir(parents=True, exist_ok=True)
    req_path.write_text("pytest\n")
    result = await install_requirements(5, repo_id=5)
    assert result is not None
    assert isinstance(result, str)