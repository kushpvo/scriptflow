import asyncio
import logging
import time
import os
from dataclasses import dataclass, field
from app.log_utils import write_log_line
from app.notifications import send_notification, should_notify_stderr

logger = logging.getLogger(__name__)

CRASH_LOOP_COUNT = 5
CRASH_LOOP_WINDOW = 60
RESTART_DELAY = 5


@dataclass
class JobProcess:
    job_id: int
    status: str = "idle"
    proc: asyncio.subprocess.Process | None = None
    crash_times: list[float] = field(default_factory=list)
    task: asyncio.Task | None = None


class ProcessManager:
    def __init__(self):
        self._jobs: dict[int, JobProcess] = {}

    def _get_or_create(self, job_id: int) -> JobProcess:
        if job_id not in self._jobs:
            self._jobs[job_id] = JobProcess(job_id=job_id)
        return self._jobs[job_id]

    def get_status(self, job_id: int) -> str:
        return self._jobs.get(job_id, JobProcess(job_id=job_id)).status

    async def start(self, job_id: int, cmd: list[str], env: dict,
                    restart_on_crash: bool, notification_url: str | None,
                    notify_on_stderr: bool) -> None:
        jp = self._get_or_create(job_id)
        if jp.status == "running":
            return
        jp.crash_times = []
        await self._launch(jp, cmd, env, restart_on_crash, notification_url, notify_on_stderr)

    async def _launch(self, jp: JobProcess, cmd: list[str], env: dict,
                      restart_on_crash: bool, notification_url: str | None,
                      notify_on_stderr: bool) -> None:
        jp.status = "running"
        try:
            jp.proc = await asyncio.create_subprocess_exec(
                *cmd, env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            jp.status = "crashed"
            write_log_line(jp.job_id, "stderr", f"Failed to start process: {e}")
            raise
        jp.task = asyncio.create_task(self._watch(
            jp, cmd, env, restart_on_crash, notification_url, notify_on_stderr
        ))

    async def _watch(self, jp: JobProcess, cmd: list[str], env: dict,
                     restart_on_crash: bool, notification_url: str | None,
                     notify_on_stderr: bool) -> None:
        # Stream stdout/stderr to log files
        stdout_task = asyncio.create_task(self._stream(jp.job_id, "stdout", jp.proc.stdout, notify_on_stderr, notification_url))
        stderr_task = asyncio.create_task(self._stream(jp.job_id, "stderr", jp.proc.stderr, notify_on_stderr, notification_url))

        # Wait for process exit, then drain remaining output from pipes
        exit_code = await jp.proc.wait()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

        # Handle non-zero exit as crash
        if exit_code != 0:
            now = time.monotonic()
            jp.crash_times.append(now)
            # Keep only crashes within the window
            jp.crash_times = [t for t in jp.crash_times if now - t <= CRASH_LOOP_WINDOW]

            if restart_on_crash:
                if len(jp.crash_times) >= CRASH_LOOP_COUNT:
                    jp.status = "crash-loop"
                    logger.warning(f"Job {jp.job_id} entered crash-loop after {len(jp.crash_times)} crashes")
                    return
                # Restart after delay
                jp.status = "crashed"
                await asyncio.sleep(RESTART_DELAY)
                if jp.status != "stopped":
                    await self._launch(jp, cmd, env, restart_on_crash, notification_url, notify_on_stderr)
        else:
            jp.status = "stopped"

    async def _stream(self, job_id: int, stream_name: str, pipe: asyncio.subprocess.PIPE,
                      notify_on_stderr: bool, notification_url: str | None) -> None:
        if pipe is None:
            return
        try:
            while True:
                line = await pipe.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                write_log_line(job_id, stream_name, decoded)
                if stream_name == "stderr" and notify_on_stderr and notification_url:
                    if should_notify_stderr(job_id):
                        await send_notification(
                            notification_url,
                            f"Job {job_id} stderr output",
                            decoded[:200]
                        )
        except asyncio.CancelledError:
            pass

    async def stop(self, job_id: int) -> None:
        jp = self._jobs.get(job_id)
        if not jp or jp.status not in ("running", "crashed", "crash-loop"):
            return
        if jp.status == "running" and jp.proc:
            jp.proc.terminate()
            try:
                await asyncio.wait_for(jp.proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                jp.proc.kill()
                await jp.proc.wait()
        jp.status = "stopped"
        if jp.task:
            jp.task.cancel()

    async def restart(self, job_id: int, cmd: list[str], env: dict,
                      restart_on_crash: bool, notification_url: str | None,
                      notify_on_stderr: bool) -> None:
        await self.stop(job_id)
        await self.start(job_id, cmd, env, restart_on_crash, notification_url, notify_on_stderr)
