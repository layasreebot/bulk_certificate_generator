
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import (
    ErrorResponse,
    JobCreate,
    JobCreatedResponse,
    JobStatusResponse,
)
from app.services.job_service import create_job, get_progress
from app.workers.tasks import process_job_task


router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
) -> JobCreatedResponse:
    try:
        job = create_job(db, payload)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create certificate job",
        ) from exc

    try:
        process_job_task.delay(str(job.id))
    except Exception as exc:
        job.status = "FAILED"
        job.error_message = "Could not enqueue certificate job"
        job.completed_at = datetime.utcnow()
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Certificate job could not be queued. Please try again.",
        ) from exc

    return JobCreatedResponse(
        id=str(job.id),
        status=job.status,
        total_recipients=job.total_recipients,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
def read_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    job = db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    progress = get_progress(db, job_id)

    return JobStatusResponse(
        id=str(job.id),
        status=job.status,
        total_recipients=job.total_recipients,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        pending_count=progress["pending_count"],
        progress_percentage=progress["progress_percentage"],
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )
