
import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.job import Job
from app.models.recipient import Recipient
from app.schemas.certificate import CertificateInfo
from app.schemas.job import JobCreate
from app.services.certificate_service import generate_certificate


logger = logging.getLogger(__name__)


def create_job(db: Session, payload: JobCreate) -> Job:
    certificate_data = payload.certificate.model_dump(mode="json")

    job = Job(
        status="PENDING",
        total_recipients=len(payload.recipients),
        certificate_data=certificate_data,
    )
    db.add(job)
    db.flush()

    recipients = [
        Recipient(
            job_id=job.id,
            name=item.name,
            email=str(item.email),
            status="PENDING",
        )
        for item in payload.recipients
    ]

    db.add_all(recipients)
    db.commit()
    db.refresh(job)

    return job


def get_job_or_none(db: Session, job_id: uuid.UUID) -> Job | None:
    return db.get(Job, job_id)


def get_progress(db: Session, job_id: uuid.UUID) -> dict:
    job = db.get(Job, job_id)

    if job is None:
        return {}

    pending_count = max(
        job.total_recipients
        - job.successful_count
        - job.failed_count,
        0,
    )

    processed_count = job.successful_count + job.failed_count

    progress = (
        round(processed_count / job.total_recipients * 100, 2)
        if job.total_recipients
        else 0.0
    )

    return {
        "total_recipients": job.total_recipients,
        "successful_count": job.successful_count,
        "failed_count": job.failed_count,
        "pending_count": pending_count,
        "progress_percentage": progress,
    }


def list_certificates(
    db: Session,
    job_id: uuid.UUID,
) -> list[Recipient]:
    statement = (
        select(Recipient)
        .where(Recipient.job_id == job_id)
        .order_by(Recipient.created_at, Recipient.id)
    )

    return list(db.scalars(statement).all())


def process_job(db_factory, job_id: str) -> None:
    db = db_factory()

    try:
        job = db.get(Job, uuid.UUID(job_id))

        if job is None:
            return

        if job.status in {
            "COMPLETED",
            "COMPLETED_WITH_ERRORS",
            "FAILED",
        }:
            return

        job.status = "PROCESSING"
        job.started_at = job.started_at or datetime.utcnow()
        db.commit()

        info = CertificateInfo.model_validate(job.certificate_data)
        settings = get_settings()

        recipients = db.scalars(
            select(Recipient)
            .where(Recipient.job_id == job.id)
            .order_by(Recipient.created_at, Recipient.id)
        ).all()

        for recipient in recipients:
            if recipient.status in {"COMPLETED", "FAILED"}:
                continue

            recipient_id = recipient.id
            recipient_name = recipient.name

            try:
                recipient.status = "PROCESSING"
                db.commit()

                relative_path = Path(str(job.id)) / f"{recipient_id}.pdf"
                output_path = (
                    Path(settings.GENERATED_CERTIFICATES_DIR)
                    / relative_path
                )

                generate_certificate(
                    recipient_name,
                    info,
                    output_path,
                )

                recipient.status = "COMPLETED"
                recipient.certificate_path = relative_path.as_posix()
                recipient.error_message = None
                recipient.completed_at = datetime.utcnow()

                db.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(
                        successful_count=Job.successful_count + 1
                    )
                )

                db.commit()

            except Exception as exc:
                logger.exception(
                    "Certificate generation failed for recipient %s",
                    recipient_id,
                )
                db.rollback()

                current_recipient = db.get(Recipient, recipient_id)

                if current_recipient is None:
                    continue

                if current_recipient.status in {"COMPLETED", "FAILED"}:
                    continue

                current_recipient.status = "FAILED"
                current_recipient.error_message = str(exc)
                current_recipient.completed_at = datetime.utcnow()

                db.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(
                        failed_count=Job.failed_count + 1
                    )
                )

                db.commit()

        db.refresh(job)

        if job.failed_count == 0:
            job.status = "COMPLETED"
        elif job.successful_count == 0:
            job.status = "FAILED"
        else:
            job.status = "COMPLETED_WITH_ERRORS"

        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Job processing failed for job %s", job_id)
        raise

    finally:
        db.close()