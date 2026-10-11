
from datetime import date

from app.models.job import Job
from app.models.recipient import Recipient
from app.services import job_service


def make_job(db, names):
    job = Job(
        status="PENDING",
        total_recipients=len(names),
        certificate_data={
            "title": "Certificate of Completion",
            "course_name": "Python Basics",
            "event_name": "Backend Bootcamp",
            "organization_name": "Example Academy",
            "issue_date": date(2026, 10, 7).isoformat(),
        },
    )
    db.add(job)
    db.flush()

    for name in names:
        db.add(
            Recipient(
                job_id=job.id,
                name=name,
                email=f"{name.lower().replace(' ', '.')}@example.com",
                status="PENDING",
            )
        )

    db.commit()
    return job.id


def fake_generator(name, info, output_path):
    if name.startswith("Fail"):
        raise RuntimeError("Test certificate failure")


def test_job_completes_when_all_certificates_succeed(
    db_session, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        job_service, "generate_certificate", fake_generator
    )
    monkeypatch.setattr(
        job_service,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {"GENERATED_CERTIFICATES_DIR": str(tmp_path)},
        )(),
    )

    job_id = make_job(db_session, ["Alex Morgan", "Jamie Lee"])
    job_service.process_job(lambda: db_session, str(job_id))

    db_session.expire_all()
    job = db_session.get(Job, job_id)

    assert job.status == "COMPLETED"
    assert job.successful_count == 2
    assert job.failed_count == 0


def test_job_fails_when_all_certificates_fail(
    db_session, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        job_service, "generate_certificate", fake_generator
    )
    monkeypatch.setattr(
        job_service,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {"GENERATED_CERTIFICATES_DIR": str(tmp_path)},
        )(),
    )

    job_id = make_job(db_session, ["Fail Alex", "Fail Jamie"])
    job_service.process_job(lambda: db_session, str(job_id))

    db_session.expire_all()
    job = db_session.get(Job, job_id)

    assert job.status == "FAILED"
    assert job.successful_count == 0
    assert job.failed_count == 2


def test_job_completes_with_errors_when_some_fail(
    db_session, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        job_service, "generate_certificate", fake_generator
    )
    monkeypatch.setattr(
        job_service,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {"GENERATED_CERTIFICATES_DIR": str(tmp_path)},
        )(),
    )

    job_id = make_job(
        db_session, ["Alex Morgan", "Fail Jamie"]
    )
    job_service.process_job(lambda: db_session, str(job_id))

    db_session.expire_all()
    job = db_session.get(Job, job_id)

    assert job.status == "COMPLETED_WITH_ERRORS"
    assert job.successful_count == 1
    assert job.failed_count == 1
def test_progress_counts_success_failed_and_pending(db_session):
    job = Job(
        status="PROCESSING",
        total_recipients=4,
        successful_count=2,
        failed_count=1,
        certificate_data={
            "title": "Certificate",
            "course_name": "Python",
            "event_name": "Bootcamp",
            "organization_name": "Example Academy",
            "issue_date": "2026-10-07",
        },
    )
    db_session.add(job)
    db_session.commit()

    result = job_service.get_progress(db_session, job.id)

    assert result["total_recipients"] == 4
    assert result["successful_count"] == 2
    assert result["failed_count"] == 1
    assert result["pending_count"] == 1
    assert result["progress_percentage"] == 75.0
