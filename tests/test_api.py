import uuid
from datetime import date
from unittest.mock import patch
import pytest

from app.models.job import Job
from app.models.recipient import Recipient


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_submit_job_success(client, db_session):
    payload = {
        "certificate": {
            "title": "Certificate of Completion",
            "course_name": "Python Basics",
            "event_name": "Backend Bootcamp",
            "organization_name": "Example Academy",
            "issue_date": "2026-10-07",
        },
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"},
        ],
    }

    with patch("app.api.routes.jobs.process_job_task.delay") as mock_delay:
        response = client.post("/api/v1/jobs", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["total_recipients"] == 2
    mock_delay.assert_called_once()

    # Verify persisted in database
    job_id = uuid.UUID(data["id"])
    job = db_session.get(Job, job_id)
    assert job is not None
    assert job.total_recipients == 2


def test_submit_job_duplicate_emails_rejected(client):
    payload = {
        "certificate": {
            "title": "Certificate of Completion",
            "course_name": "Python Basics",
            "event_name": "Backend Bootcamp",
            "organization_name": "Example Academy",
            "issue_date": "2026-10-07",
        },
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Alice Duplicate", "email": "alice@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_submit_job_empty_recipients_rejected(client):
    payload = {
        "certificate": {
            "title": "Certificate of Completion",
            "course_name": "Python Basics",
            "event_name": "Backend Bootcamp",
            "organization_name": "Example Academy",
            "issue_date": "2026-10-07",
        },
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


def test_submit_job_queue_failure_returns_503(client, db_session):
    payload = {
        "certificate": {
            "title": "Certificate of Completion",
            "course_name": "Python Basics",
            "event_name": "Backend Bootcamp",
            "organization_name": "Example Academy",
            "issue_date": "2026-10-07",
        },
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
        ],
    }

    with patch(
        "app.api.routes.jobs.process_job_task.delay",
        side_effect=RuntimeError("Redis down"),
    ):
        response = client.post("/api/v1/jobs", json=payload)

    assert response.status_code == 503
    assert "Certificate job could not be queued" in response.json()["detail"]


def test_get_job_status(client, db_session):
    job = Job(
        status="PROCESSING",
        total_recipients=5,
        successful_count=2,
        failed_count=1,
        certificate_data={"title": "Test"},
    )
    db_session.add(job)
    db_session.commit()

    response = client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(job.id)
    assert data["status"] == "PROCESSING"
    assert data["total_recipients"] == 5
    assert data["successful_count"] == 2
    assert data["failed_count"] == 1
    assert data["pending_count"] == 2
    assert data["progress_percentage"] == 60.0


def test_get_job_status_not_found(client):
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/jobs/{random_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_get_job_certificates(client, db_session):
    job = Job(
        status="COMPLETED",
        total_recipients=2,
        successful_count=1,
        failed_count=1,
        certificate_data={"title": "Test"},
    )
    db_session.add(job)
    db_session.flush()

    r1 = Recipient(
        job_id=job.id,
        name="Alex",
        email="alex@example.com",
        status="COMPLETED",
        certificate_path=f"{job.id}/alex.pdf",
    )
    r2 = Recipient(
        job_id=job.id,
        name="Sam",
        email="sam@example.com",
        status="FAILED",
        error_message="Error generating",
    )
    db_session.add_all([r1, r2])
    db_session.commit()

    # Get all certificates
    response = client.get(f"/api/v1/jobs/{job.id}/certificates")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == str(job.id)
    assert len(data["certificates"]) == 2

    alex_item = next(c for c in data["certificates"] if c["name"] == "Alex")
    assert alex_item["download_url"] == f"/api/v1/certificates/{alex_item['id']}/download"

    # Filter by status
    response_filter = client.get(f"/api/v1/jobs/{job.id}/certificates?status=COMPLETED")
    assert response_filter.status_code == 200
    filtered_certs = response_filter.json()["certificates"]
    assert len(filtered_certs) == 1
    assert filtered_certs[0]["name"] == "Alex"

    # Invalid status filter
    response_invalid = client.get(f"/api/v1/jobs/{job.id}/certificates?status=INVALID_STATUS")
    assert response_invalid.status_code == 422


def test_get_job_certificates_job_not_found(client):
    response = client.get(f"/api/v1/jobs/{uuid.uuid4()}/certificates")
    assert response.status_code == 404


def test_download_certificate(client, db_session, tmp_path, monkeypatch):
    job = Job(
        status="COMPLETED",
        total_recipients=1,
        certificate_data={"title": "Test"},
    )
    db_session.add(job)
    db_session.flush()

    pdf_file = tmp_path / f"{job.id}" / "cert.pdf"
    pdf_file.parent.mkdir(parents=True, exist_ok=True)
    pdf_file.write_bytes(b"%PDF-1.4 test certificate content")

    recipient = Recipient(
        job_id=job.id,
        name="Alex",
        email="alex@example.com",
        status="COMPLETED",
        certificate_path=f"{job.id}/cert.pdf",
    )
    db_session.add(recipient)
    db_session.commit()

    # Monkeypatch settings to point to tmp_path
    monkeypatch.setattr(
        "app.api.routes.certificates.get_settings",
        lambda: type("Settings", (), {"GENERATED_CERTIFICATES_DIR": str(tmp_path)})(),
    )

    response = client.get(f"/api/v1/certificates/{recipient.id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_download_certificate_not_found(client):
    response = client.get(f"/api/v1/certificates/{uuid.uuid4()}/download")
    assert response.status_code == 404


def test_download_certificate_not_ready(client, db_session):
    job = Job(
        status="PENDING",
        total_recipients=1,
        certificate_data={"title": "Test"},
    )
    db_session.add(job)
    db_session.flush()

    recipient = Recipient(
        job_id=job.id,
        name="Alex",
        email="alex@example.com",
        status="PENDING",
    )
    db_session.add(recipient)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{recipient.id}/download")
    assert response.status_code == 409
    assert response.json()["detail"] == "Certificate is not ready for download"
