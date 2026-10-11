
import os
import tempfile
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from app.templates.certificate_template import draw_certificate


def generate_certificate(
    name: str,
    info: object,
    output_path: str | Path,
) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=destination.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        pdf = canvas.Canvas(
            str(temp_path),
            pagesize=landscape(A4),
        )

        draw_certificate(pdf, name, info)
        pdf.save()

        os.replace(temp_path, destination)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
