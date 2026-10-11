
from celery import Celery

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.job_service import process_job


settings = get_settings()

celery_app = Celery(
    "certificate_generator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


@celery_app.task(
    name="process_job_task",
    acks_late=True,
)
def process_job_task(job_id: str) -> None:
    process_job(SessionLocal, job_id)
