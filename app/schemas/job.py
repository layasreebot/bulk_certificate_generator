
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.core.config import get_settings
from app.schemas.certificate import CertificateInfo
from app.schemas.recipient import CertificateItem, RecipientIn


settings = get_settings()


class JobCreate(BaseModel):
    certificate: CertificateInfo
    recipients: list[RecipientIn] = Field(
        min_length=1,
        max_length=settings.MAX_RECIPIENTS_PER_JOB,
    )

    @field_validator("recipients")
    @classmethod
    def check_duplicate_emails(
        cls,
        recipients: list[RecipientIn],
    ) -> list[RecipientIn]:
        seen_emails = set()

        for recipient in recipients:
            email = recipient.email.lower()

            if email in seen_emails:
                raise ValueError("Duplicate recipient emails are not allowed")

            seen_emails.add(email)

        return recipients

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "certificate": {
                    "title": "Certificate of Completion",
                    "course_name": "Python Basics",
                    "event_name": "Backend Bootcamp",
                    "organization_name": "Example Academy",
                    "issue_date": "2026-10-07",
                },
                "recipients": [
                    {
                        "name": "Alex Morgan",
                        "email": "alex@example.com",
                    }
                ],
            }
        }
    )


class JobCreatedResponse(BaseModel):
    id: str
    status: str
    total_recipients: int


class JobStatusResponse(BaseModel):
    id: str
    status: str
    total_recipients: int
    successful_count: int
    failed_count: int
    pending_count: int
    progress_percentage: float
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class JobCertificatesResponse(BaseModel):
    job_id: str
    certificates: list[CertificateItem]


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
