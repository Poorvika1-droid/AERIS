from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery("aeris", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery_app.conf.task_routes = {"aeris.jobs.*": {"queue": "aeris"}}
celery_app.conf.timezone = "UTC"


@celery_app.task(name="aeris.jobs.continuous_learning")
def continuous_learning_task() -> dict:
    from app.db import SessionLocal
    from app.pipeline import learning_step

    db = SessionLocal()
    try:
        return learning_step(db)
    finally:
        db.close()
