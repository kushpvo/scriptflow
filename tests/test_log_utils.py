import os
from datetime import date, timedelta
import pytest
from app.log_utils import write_log_line, read_log_file, list_log_dates, rotate_logs


def test_write_and_read_log(tmp_data_dir):
    write_log_line(job_id=1, stream="stdout", message="hello world")
    today = date.today()
    lines = read_log_file(1, today)
    assert any("hello world" in l for l in lines)
    assert any("[stdout]" in l for l in lines)


def test_read_with_stream_filter(tmp_data_dir):
    write_log_line(job_id=2, stream="stdout", message="out msg")
    write_log_line(job_id=2, stream="stderr", message="err msg")
    today = date.today()
    stdout_lines = read_log_file(2, today, stream_filter="stdout")
    assert all("[stdout]" in l for l in stdout_lines)
    assert not any("[stderr]" in l for l in stdout_lines)


def test_list_log_dates(tmp_data_dir):
    write_log_line(job_id=3, stream="stdout", message="x")
    dates = list_log_dates(3)
    assert len(dates) >= 1
    assert dates[0] == date.today().isoformat()


def test_read_nonexistent_log(tmp_data_dir):
    lines = read_log_file(999, date.today())
    assert lines == []


def test_rotate_logs(tmp_data_dir):
    log_dir = os.path.join(tmp_data_dir, "logs", "4")
    os.makedirs(log_dir)
    old = os.path.join(log_dir, (date.today() - timedelta(days=40)).isoformat() + ".log")
    recent = os.path.join(log_dir, date.today().isoformat() + ".log")
    open(old, "w").write("old")
    open(recent, "w").write("new")
    deleted = rotate_logs(retention_days=30)
    assert deleted == 1
    assert not os.path.exists(old)
    assert os.path.exists(recent)