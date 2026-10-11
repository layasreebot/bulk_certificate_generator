
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.job import Job
from app.models.recipient import Recipient
from app.schemas.job import ErrorResponse, JobCertificatesResponse
from app.schemas.recipient import CertificateItem
from app.services.job_service import list_certificates


router = APIRouter(tags=["Certificates"])


@router.get(
    "/api/v1/jobs/{job_id}/certificates",
    response_model=JobCertificatesResponse,
)
def read_certificates(
    job_id: uuid.UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> JobCertificatesResponse:
    job = db.get(Job, job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if status_filter is not None:
        status_filter = status_filter.upper()
        allowed = {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}

        if status_filter not in allowed:
            raise HTTPException(
                status_code=422,
                detail="Invalid recipient status",
            )

        recipients = db.scalars(
            select(Recipient)
            .where(
                Recipient.job_id == job_id,
                Recipient.status == status_filter,
            )
            .order_by(Recipient.created_at, Recipient.id)
        ).all()
    else:
        recipients = list_certificates(db, job_id)

    items = [
        CertificateItem(
            id=str(item.id),
            name=item.name,
            email=item.email,
            status=item.status,
            download_url=(
                f"/api/v1/certificates/{item.id}/download"
                if item.status == "COMPLETED"
                else None
            ),
            error_message=item.error_message,
        )
        for item in recipients
    ]

    return JobCertificatesResponse(
        job_id=str(job.id),
        certificates=items,
    )


@router.get(
    "/api/v1/certificates/{certificate_id}/download",
    responses={404: {"model": ErrorResponse}},
)
def download_certificate(
    certificate_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> FileResponse:
    recipient = db.get(Recipient, certificate_id)

    if recipient is None:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if recipient.status != "COMPLETED" or not recipient.certificate_path:
        raise HTTPException(
            status_code=409,
            detail="Certificate is not ready for download",
        )

    settings = get_settings()
    base_dir = Path(settings.GENERATED_CERTIFICATES_DIR).resolve()
    file_path = (base_dir / recipient.certificate_path).resolve()

    if not file_path.is_relative_to(base_dir):
        raise HTTPException(status_code=404, detail="Certificate not found")

    if not file_path.is_file():
        raise HTTPException(
            status_code=410,
            detail="Certificate file is no longer available",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"{recipient.id}.pdf",
    )