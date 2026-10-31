"""Server-side PDF export of a report (reportlab, pure Python, free)."""
import base64
import io
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .analysis import TEST_NAME
from .models import FacilitySettings, Report
from .qr import qr_png_bytes

BRAND = colors.HexColor("#b3182d")


def _data_uri_bytes(uri: str) -> bytes | None:
    try:
        return base64.b64decode(uri.split(",", 1)[1])
    except Exception:
        return None


def _flowable_image(raw: bytes, max_w: float, max_h: float):
    with PILImage.open(io.BytesIO(raw)) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    return Image(io.BytesIO(raw), width=w * scale, height=h * scale)


def _result_text(r: Report) -> str:
    if r.result == "blast_detected":
        return f"{r.total_blasts} blast cell region(s) found"
    if r.result == "normal":
        return "No blast cells were found"
    return "Unknown - samples could not be analysed"


def build_report_pdf(r: Report, f: FacilitySettings, verify_url: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=f"LeukNet report {r.id}")
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor("#555555"))
    h_fac = ParagraphStyle("fac", parent=ss["Heading2"], fontSize=15, spaceAfter=2, textColor=colors.black)
    title = ParagraphStyle("title", parent=ss["Heading1"], fontSize=12.5, alignment=1, spaceBefore=6, spaceAfter=8)
    h3 = ParagraphStyle("h3", parent=ss["Heading3"], fontSize=10, textColor=BRAND, spaceBefore=10, spaceAfter=4)
    P = lambda t, st=body: Paragraph(escape(str(t)), st)

    story = []
    head_cells = []
    logo = _data_uri_bytes(f.logo_data_url) if f.logo_data_url else None
    if logo:
        try:
            head_cells.append(_flowable_image(logo, 28 * mm, 22 * mm))
        except Exception:
            logo = None
    contact_line = "  |  ".join(x for x in (f.address, f.contact, f.email) if x)
    text_block = [P(f.facility_name, h_fac), P(contact_line, small)]
    head = Table([[head_cells[0], text_block]] if logo else [[text_block]], colWidths=[32 * mm, None] if logo else None)
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 2, BRAND),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [head, Paragraph("LEUKNET BLOOD SMEAR SCREENING REPORT", title)]

    p = r.patient
    kv_style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d6e0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f5f8")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    when = r.created_at.strftime("%d %b %Y, %H:%M UTC")
    patient_rows = [["Patient name", P(p.name)], ["Patient address", P(p.address or "-")],
                    ["Patient contact", P(p.contact or "-")], ["Report date", when], ["Report ID", P(r.id, small)]]
    t = Table(patient_rows, colWidths=[38 * mm, 140 * mm]); t.setStyle(kv_style); story.append(t)

    story.append(Paragraph("SUMMARY", h3))
    summary_rows = [["Gender", p.gender], ["Age", f"{p.age} years"], ["Test", TEST_NAME],
                    ["Samples analysed", f"{r.images_analyzed} of {r.sample_size}"],
                    ["Total blast cells", _result_text(r)], ["Foreign objects", str(r.foreign_objects)]]
    t = Table(summary_rows, colWidths=[38 * mm, 140 * mm]); t.setStyle(kv_style); story.append(t)

    story.append(Paragraph("RESULTS REPORT", h3))
    tone = {"blast_detected": BRAND, "normal": colors.HexColor("#17794a")}.get(r.result, colors.HexColor("#9a6200"))
    box = Table([[Paragraph(escape(r.summary), body)]], colWidths=[178 * mm])
    box.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, tone), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f7f9")),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(box)

    imgs = [(x["filename"], _data_uri_bytes(x.get("annotated_image", ""))) for x in r.findings]
    imgs = [(n, b) for n, b in imgs if b]
    if imgs:
        story.append(Paragraph("ANALYSED SAMPLES", h3))
        cells = []
        for name, raw in imgs:
            try:
                cells.append([_flowable_image(raw, 82 * mm, 62 * mm), P(name, small)])
            except Exception:
                continue
        rows = [cells[i:i + 2] for i in range(0, len(cells), 2)]
        grid = Table([[c for c in row] + [""] * (2 - len(row)) for row in rows], colWidths=[88 * mm, 88 * mm])
        grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(grid)

    qr = Image(io.BytesIO(qr_png_bytes(verify_url)), width=30 * mm, height=30 * mm)
    foot = Table([[qr, [P("Verify this report", ParagraphStyle("b", parent=body, fontName="Helvetica-Bold")),
                        P("Scan the QR code or open:", small), P(verify_url, small)]]], colWidths=[34 * mm, None])
    foot.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#d0d6e0")),
                              ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    story += [Spacer(1, 8), KeepTogether([foot, Spacer(1, 6), P(f.report_footer, small)])]

    doc.build(story)
    return buf.getvalue()
