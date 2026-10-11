from pathlib import Path
from types import SimpleNamespace
from datetime import date

from app.services.certificate_service import generate_certificate

output_path = Path("generated_certificates/test_certificate.pdf")

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

with output_path.open("rb") as pdf_file:
    header = pdf_file.read(4)

assert header == b"%PDF", f"Invalid PDF header: {header!r}"
assert output_path.stat().st_size > 0, "PDF file is empty"

print("PASS: PDF generated successfully")
print("PDF size:", output_path.stat().st_size, "bytes")
print("PDF path:", output_path)