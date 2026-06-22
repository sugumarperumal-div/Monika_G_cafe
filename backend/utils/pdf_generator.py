from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import io
from datetime import datetime


BRAND_BROWN = colors.HexColor("#6B3F1A")
BRAND_TAN   = colors.HexColor("#C17B3F")
LIGHT_BG    = colors.HexColor("#FDF6EE")


def generate_invoice_pdf(invoice_data: dict) -> bytes:
    """
    invoice_data keys:
      invoice_number, order_number, issued_at,
      customer_name, customer_phone, customer_email,
      items: [{name, qty, unit_price, total}],
      subtotal, discount_amount, gst_amount, total_amount,
      payment_method, payment_reference
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                  textColor=BRAND_BROWN, alignment=TA_CENTER, fontSize=20)
    sub_style   = ParagraphStyle("Sub", parent=styles["Normal"],
                                  textColor=BRAND_TAN, alignment=TA_CENTER, fontSize=10)
    right_style = ParagraphStyle("Right", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=9)
    normal      = styles["Normal"]

    story = []

    # ── Header ──
    story.append(Paragraph("Monika G Cafe", title_style))
    story.append(Paragraph("Great Coffee · Great Company", sub_style))
    story.append(Spacer(1, 6*mm))

    # ── Invoice meta ──
    meta = [
        ["Invoice #", invoice_data.get("invoice_number", ""), "Order #", invoice_data.get("order_number", "")],
        ["Date",      invoice_data.get("issued_at", datetime.now().strftime("%d %b %Y %H:%M")),
         "Payment",   invoice_data.get("payment_method", "").upper()],
    ]
    if invoice_data.get("customer_name"):
        meta.append(["Customer", invoice_data["customer_name"], "Phone", invoice_data.get("customer_phone", "")])

    meta_table = Table(meta, colWidths=[30*mm, 65*mm, 30*mm, 45*mm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_BROWN),
        ("TEXTCOLOR", (2, 0), (2, -1), BRAND_BROWN),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6*mm))

    # ── Items ──
    item_header = [["#", "Item", "Qty", "Unit Price", "Total"]]
    item_rows = []
    for i, item in enumerate(invoice_data.get("items", []), 1):
        item_rows.append([
            str(i),
            item["name"],
            str(item["qty"]),
            f"₹{item['unit_price']:.2f}",
            f"₹{item['total']:.2f}",
        ])

    items_table = Table(
        item_header + item_rows,
        colWidths=[10*mm, 80*mm, 15*mm, 30*mm, 35*mm]
    )
    items_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BRAND_BROWN),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ALIGN",        (2, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4*mm))

    # ── Totals ──
    totals = [
        ["Subtotal", f"₹{invoice_data.get('subtotal', 0):.2f}"],
        ["Discount", f"-₹{invoice_data.get('discount_amount', 0):.2f}"],
        ["GST",      f"₹{invoice_data.get('gst_amount', 0):.2f}"],
        ["TOTAL",    f"₹{invoice_data.get('total_amount', 0):.2f}"],
    ]
    totals_table = Table(totals, colWidths=[130*mm, 40*mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME",     (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, -1), (-1, -1), 12),
        ("TEXTCOLOR",    (0, -1), (-1, -1), BRAND_BROWN),
        ("LINEABOVE",    (0, -1), (-1, -1), 1, BRAND_BROWN),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 8*mm))

    # ── Footer ──
    story.append(Paragraph(
        "Thank you for visiting Monika G Cafe! We hope to see you again.",
        ParagraphStyle("Footer", parent=normal, alignment=TA_CENTER,
                       textColor=BRAND_TAN, fontSize=9)
    ))

    doc.build(story)
    return buffer.getvalue()