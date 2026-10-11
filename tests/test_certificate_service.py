from datetime import date
from pathlib import Path
from types import SimpleNamespace
import pytest

from app.services.certificate_service import generate_certificate


def test_generate_certificate_creates_valid_pdf(tmp_path):
    output_path = tmp_path / "test_certificate.pdf"
    info = SimpleNamespace(
        title="Certificate of Completion",
        course_name="Python Basics",
        event_name="Backend Bootcamp",
        organization_name="Example Academy",
        issue_date=date(2026, 10, 7),
    )

    generate_certificate(
        name="Alex Morgan",
        info=info,
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    with output_path.open("rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


def test_generate_certificate_with_string_date(tmp_path):
    output_path = tmp_path / "string_date.pdf"
    info = SimpleNamespace(
        title="Certificate of Completion",
        course_name="Python Basics",
        event_name="Backend Bootcamp",
        organization_name="Example Academy",
        issue_date="2026-10-07",
    )

    generate_certificate(
        name="Taylor Swift",
        info=info,
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_draw_recipient_name_scales_down_for_long_name(tmp_path):
    output_path = tmp_path / "long_name.pdf"
    info = SimpleNamespace(
        title="Certificate of Excellence",
        course_name="Advanced Cloud Architecture",
        event_name="Global Summit",
        organization_name="World Tech Institute",
        issue_date=date(2026, 10, 7),
    )

    generate_certificate(
        name="Alexandrina Victoria Sophia Charlotte Elizabeth Montgomery",
        info=info,
        output_path=output_path,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_certificate_cleans_up_on_failure(tmp_path, monkeypatch):
    from app.services import certificate_service

    def failing_draw(*args, **kwargs):
        raise ValueError("Simulated PDF draw failure")

    monkeypatch.setattr(certificate_service, "draw_certificate", failing_draw)

    output_path = tmp_path / "failed.pdf"
    info = SimpleNamespace(
        title="Certificate",
        course_name="Python",
        event_name="Bootcamp",
        organization_name="Academy",
        issue_date=date(2026, 10, 7),
    )

    with pytest.raises(ValueError, match="Simulated PDF draw failure"):
        generate_certificate("Alex", info, output_path)

    assert not output_path.exists()
    # Ensure temporary files in directory were also unlinked
    temp_files = list(tmp_path.glob("*.pdf"))
    assert len(temp_files) == 0
