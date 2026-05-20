from __future__ import annotations

import queue
import threading
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Callable


JobHandler = Callable[..., dict[str, Any]]

_queue: queue.Queue[tuple[str, JobHandler, list[str], tuple[Any, ...]]] = queue.Queue()
_jobs: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()
_started = False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_worker() -> None:
    global _started
    with _lock:
        if _started:
            return
        _started = True
    thread = threading.Thread(target=_run, name="listing-import-worker", daemon=True)
    thread.start()


def enqueue_import(handler: JobHandler, urls: list[str], *args: Any) -> dict[str, Any]:
    start_worker()
    job_id = uuid.uuid4().hex
    job = {
        "id": job_id,
        "status": "queued",
        "total": len(urls),
        "processed": 0,
        "imported": 0,
        "skipped": 0,
        "message": "Queued",
        "listings": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    with _lock:
        _jobs[job_id] = job
    _queue.put((job_id, handler, urls, args))
    return job.copy()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return job.copy() if job else None


def update_job(job_id: str, **values: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.update(values)
        job["updated_at"] = now_iso()


def _run() -> None:
    while True:
        job_id, handler, urls, args = _queue.get()
        update_job(job_id, status="running", message="Importing listings")
        try:
            result = handler(job_id, urls, *args)
            update_job(job_id, status="completed", message="Import completed", **result)
        except Exception as exc:
            update_job(
                job_id,
                status="failed",
                message=f"{type(exc).__name__}: {exc}",
                traceback=traceback.format_exc(),
            )
        finally:
            _queue.task_done()
