from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def draw_centered_text(
    pdf: canvas.Canvas,
    text: str,
    y: float,
    font: str = "Helvetica",
    size: int = 16,
) -> None:
    page_width, _ = landscape(A4)
    pdf.setFont(font, size)
    pdf.drawCentredString(page_width / 2, y, text)


def draw_recipient_name(
    pdf: canvas.Canvas,
    name: str,
    y: float,
) -> None:
    page_width, _ = landscape(A4)
    max_width = page_width - 100
    font_size = 36

    while (
        pdf.stringWidth(name, "Helvetica-Bold", font_size) > max_width
        and font_size > 18
    ):
        font_size -= 1

    pdf.setFont("Helvetica-Bold", font_size)
    pdf.drawCentredString(page_width / 2, y, name)


def draw_certificate(
    pdf: canvas.Canvas,
    name: str,
    info: object,
) -> None:
    page_width, page_height = landscape(A4)

    # Double border gives the certificate a formal appearance.
    pdf.setLineWidth(3)
    pdf.rect(25, 25, page_width - 50, page_height - 50)

    pdf.setLineWidth(1)
    pdf.rect(35, 35, page_width - 70, page_height - 70)

    draw_centered_text(
        pdf, info.title, page_height - 105,
        "Helvetica-Bold", 30,
    )
    draw_centered_text(
        pdf, "This is to certify that", page_height - 175,
    )

    draw_recipient_name(pdf, name, page_height - 235)

    draw_centered_text(
        pdf, "has successfully completed", page_height - 280,
    )
    draw_centered_text(
        pdf, info.course_name, page_height - 325,
        "Helvetica-Bold", 23,
    )
    draw_centered_text(
        pdf, info.event_name, page_height - 365,
    )
    draw_centered_text(
        pdf, info.organization_name, page_height - 420,
        "Helvetica-Bold", 17,
    )

    issue_date = info.issue_date
    if isinstance(issue_date, str):
        issue_date = date.fromisoformat(issue_date)

    draw_centered_text(
        pdf,
        issue_date.strftime("%d %b %Y"),
        75,
        "Helvetica",
        13,
    )