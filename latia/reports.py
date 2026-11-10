from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

GREEN = colors.HexColor("#145A3B")
INK = colors.HexColor("#252525")
MUTED = colors.HexColor("#626762")
BORDER = colors.HexColor("#E2E6DF")
MARGIN = 42


def report_footer(canvas, document):
    canvas.setStrokeColor(BORDER)
    canvas.line(MARGIN, 38, A4[0] - MARGIN, 38)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(MARGIN, 24, "LATIA | Diario de presión arterial")
    canvas.drawRightString(A4[0] - MARGIN, 24, f"Página {document.page}")


def readings_pdf(rows, zone, period):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title="LATIA - Historial de lecturas", author="LATIA",
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=38, bottomMargin=52,
    )
    heading = ParagraphStyle("Heading", fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=GREEN)
    meta = ParagraphStyle("Meta", fontName="Helvetica", fontSize=10, leading=14, textColor=MUTED)
    note = ParagraphStyle("Note", fontName="Helvetica", fontSize=9, leading=13, textColor=INK)
    count = f"{len(rows)} {'lectura' if len(rows) == 1 else 'lecturas'}"
    story = [
        Paragraph("Historial de lecturas", heading),
        Spacer(1, 8),
        Paragraph(escape(f"{period} | {count} | {zone.key}"), meta),
        Spacer(1, 18),
    ]
    if rows:
        entries = [["Fecha y hora", "Sistólica\n(mmHg)", "Diastólica\n(mmHg)", "Pulso\n(lpm)", "Comentario"]]
        for row in rows:
            measured_at = row.measured_at.astimezone(zone).strftime("%d/%m/%Y\n%H:%M")
            comment = escape(" ".join(row.note.split())) or "-"
            entries.append([measured_at, row.systolic, row.diastolic, row.pulse, Paragraph(comment, note)])
        columns = [86, 66, 66, 54]
        columns.append(doc.width - 12 - sum(columns))
        table = LongTable(entries, colWidths=columns, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEADING", (0, 0), (-1, -1), 12),
            ("ALIGN", (1, 0), (3, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F4")]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No hay lecturas en el período seleccionado.", note))

    doc.build(story, onFirstPage=report_footer, onLaterPages=report_footer)
    buffer.seek(0)
    return buffer
