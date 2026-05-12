import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from backend.config import settings

# Color palette
PRIMARY = colors.HexColor("#1a73e8")
DARK = colors.HexColor("#1a1a2e")
LIGHT_GRAY = colors.HexColor("#f8f9fa")
MID_GRAY = colors.HexColor("#dee2e6")
TEXT_GRAY = colors.HexColor("#6c757d")
GREEN = colors.HexColor("#28a745")
ORANGE = colors.HexColor("#fd7e14")


def format_inr(amount: float) -> str:
    """Format amount in Indian number system."""
    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount/100000:.2f} L"
    s = f"{amount:,.2f}"
    return f"₹{s}"


def _build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontSize=22, fontName="Helvetica-Bold",
                                textColor=PRIMARY, alignment=TA_LEFT),
        "subtitle": ParagraphStyle("subtitle", fontSize=10, fontName="Helvetica",
                                   textColor=TEXT_GRAY, alignment=TA_LEFT),
        "heading": ParagraphStyle("heading", fontSize=11, fontName="Helvetica-Bold",
                                  textColor=DARK),
        "normal": ParagraphStyle("normal", fontSize=9, fontName="Helvetica",
                                 textColor=DARK, leading=14),
        "small": ParagraphStyle("small", fontSize=8, fontName="Helvetica",
                                textColor=TEXT_GRAY),
        "right": ParagraphStyle("right", fontSize=9, fontName="Helvetica",
                                textColor=DARK, alignment=TA_RIGHT),
        "bold_right": ParagraphStyle("bold_right", fontSize=10, fontName="Helvetica-Bold",
                                     textColor=DARK, alignment=TA_RIGHT),
        "total": ParagraphStyle("total", fontSize=12, fontName="Helvetica-Bold",
                                textColor=PRIMARY, alignment=TA_RIGHT),
        "center": ParagraphStyle("center", fontSize=9, fontName="Helvetica",
                                 textColor=TEXT_GRAY, alignment=TA_CENTER),
    }


def generate_quotation_pdf(quotation) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm
    )
    styles = _build_styles()
    story = []

    # ── Header ──────────────────────────────────────────────
    header_data = [
        [
            Paragraph(settings.BUSINESS_NAME, styles["title"]),
            Paragraph("QUOTATION", ParagraphStyle(
                "qt", fontSize=24, fontName="Helvetica-Bold",
                textColor=PRIMARY, alignment=TA_RIGHT))
        ],
        [
            Paragraph(
                f"{settings.BUSINESS_ADDRESS}<br/>"
                f"Ph: {settings.BUSINESS_PHONE} | {settings.BUSINESS_EMAIL}<br/>"
                f"GSTIN: {settings.BUSINESS_GST}",
                styles["small"]),
            Paragraph(
                f"<b>Quote #:</b> {quotation.quote_number}<br/>"
                f"<b>Date:</b> {quotation.created_at.strftime('%d-%b-%Y')}<br/>"
                f"<b>Valid Until:</b> {quotation.valid_until.strftime('%d-%b-%Y')}",
                ParagraphStyle("hdr_right", fontSize=9, fontName="Helvetica",
                               alignment=TA_RIGHT, leading=14)),
        ]
    ]
    header_table = Table(header_data, colWidths=[100*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=6))

    # ── Bill To ──────────────────────────────────────────────
    cust = quotation.customer
    bill_to_text = (
        f"<b>Bill To:</b><br/>"
        f"<b>{cust.name}</b><br/>"
        f"{cust.company + '<br/>' if cust.company else ''}"
        f"{cust.address or ''}<br/>"
        f"{cust.phone or ''}"
        f"{' | ' + cust.email if cust.email else ''}"
        f"{'<br/>GSTIN: ' + cust.gstin if cust.gstin else ''}"
    )
    bill_table = Table(
        [[Paragraph(bill_to_text, styles["normal"])]],
        colWidths=[180*mm]
    )
    bill_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 6))

    # ── Items Table ──────────────────────────────────────────
    col_headers = ["#", "Description", "HSN", "Qty", "Unit", "Rate (₹)", "Amount (₹)"]
    rows = [col_headers]
    for i, item in enumerate(quotation.items, 1):
        rows.append([
            str(i),
            item.description,
            item.hsn_code or "-",
            f"{item.quantity:g}",
            item.unit,
            f"{item.unit_price:,.2f}",
            f"{item.line_total:,.2f}",
        ])

    col_widths = [10*mm, 65*mm, 18*mm, 15*mm, 15*mm, 25*mm, 25*mm]
    items_table = Table(rows, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, MID_GRAY),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4))

    # ── Totals ────────────────────────────────────────────────
    totals_data = [
        ["", "Subtotal:", format_inr(quotation.subtotal)],
    ]
    if quotation.discount_percent > 0:
        totals_data.append([
            "", f"Discount ({quotation.discount_percent:.1f}%):",
            f"-{format_inr(quotation.discount_amount)}"
        ])
    totals_data.append(["", f"GST ({quotation.tax_percent:.0f}%):", format_inr(quotation.tax_amount)])
    totals_data.append(["", "TOTAL:", format_inr(quotation.total)])

    totals_table = Table(totals_data, colWidths=[103*mm, 45*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (1, -1), (-1, -1), 11),
        ("TEXTCOLOR", (1, -1), (-1, -1), PRIMARY),
        ("LINEABOVE", (1, -1), (-1, -1), 1, PRIMARY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY, spaceAfter=6))

    # ── Terms ─────────────────────────────────────────────────
    terms_data = [
        [
            Paragraph(f"<b>Payment Terms:</b> {quotation.payment_terms}", styles["small"]),
            Paragraph(f"<b>Delivery Terms:</b> {quotation.delivery_terms}", styles["small"]),
        ]
    ]
    if quotation.notes:
        terms_data.append([
            Paragraph(f"<b>Notes:</b> {quotation.notes}", styles["small"]),
            Paragraph("", styles["small"]),
        ])
    terms_table = Table(terms_data, colWidths=[90*mm, 90*mm])
    terms_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
    ]))
    story.append(terms_table)
    story.append(Spacer(1, 10))

    # ── Signature ─────────────────────────────────────────────
    sig_data = [
        [
            Paragraph("Customer Acceptance", styles["small"]),
            Paragraph("For " + settings.BUSINESS_NAME, styles["small"]),
        ],
        [
            Paragraph("<br/><br/>___________________________<br/>Signature & Date", styles["small"]),
            Paragraph("<br/><br/>___________________________<br/>Authorized Signatory", styles["small"]),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[90*mm, 90*mm])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(sig_table)

    # ── Footer ────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceBefore=6))
    story.append(Paragraph(
        "This is a computer generated quotation. Subject to jurisdiction of local courts.",
        styles["center"]
    ))

    doc.build(story)
    return buffer.getvalue()


def generate_invoice_pdf(order) -> bytes:
    """Generate invoice PDF from an order (reuses quote PDF structure with invoice branding)."""
    quotation = order.quotation
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm
    )
    styles = _build_styles()
    story = []

    header_data = [
        [
            Paragraph(settings.BUSINESS_NAME, styles["title"]),
            Paragraph("TAX INVOICE", ParagraphStyle(
                "inv", fontSize=22, fontName="Helvetica-Bold",
                textColor=GREEN, alignment=TA_RIGHT))
        ],
        [
            Paragraph(
                f"{settings.BUSINESS_ADDRESS}<br/>"
                f"Ph: {settings.BUSINESS_PHONE} | {settings.BUSINESS_EMAIL}<br/>"
                f"GSTIN: {settings.BUSINESS_GST}",
                styles["small"]),
            Paragraph(
                f"<b>Invoice #:</b> {order.invoice_number}<br/>"
                f"<b>Order #:</b> {order.order_number}<br/>"
                f"<b>Date:</b> {order.created_at.strftime('%d-%b-%Y')}<br/>"
                f"<b>Quote Ref:</b> {quotation.quote_number}",
                ParagraphStyle("hdr_right", fontSize=9, fontName="Helvetica",
                               alignment=TA_RIGHT, leading=14)),
        ]
    ]
    header_table = Table(header_data, colWidths=[100*mm, 80*mm])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN, spaceAfter=6))

    cust = quotation.customer
    bill_to_text = (
        f"<b>Bill To:</b><br/><b>{cust.name}</b><br/>"
        f"{cust.company + '<br/>' if cust.company else ''}"
        f"{cust.address or ''}<br/>{cust.phone or ''}"
        f"{' | ' + cust.email if cust.email else ''}"
        f"{'<br/>GSTIN: ' + cust.gstin if cust.gstin else ''}"
    )
    bill_table = Table([[Paragraph(bill_to_text, styles["normal"])]], colWidths=[180*mm])
    bill_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 6))

    col_headers = ["#", "Description", "HSN", "Qty", "Unit", "Rate (₹)", "Amount (₹)"]
    rows = [col_headers]
    for i, item in enumerate(quotation.items, 1):
        rows.append([
            str(i), item.description, item.hsn_code or "-",
            f"{item.quantity:g}", item.unit,
            f"{item.unit_price:,.2f}", f"{item.line_total:,.2f}",
        ])

    col_widths = [10*mm, 65*mm, 18*mm, 15*mm, 15*mm, 25*mm, 25*mm]
    items_table = Table(rows, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("BOX", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, MID_GRAY),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4))

    totals_data = [["", "Subtotal:", format_inr(quotation.subtotal)]]
    if quotation.discount_percent > 0:
        totals_data.append([
            "", f"Discount ({quotation.discount_percent:.1f}%):",
            f"-{format_inr(quotation.discount_amount)}"
        ])
    totals_data.append(["", f"GST ({quotation.tax_percent:.0f}%):", format_inr(quotation.tax_amount)])
    totals_data.append(["", "TOTAL:", format_inr(quotation.total)])

    totals_table = Table(totals_data, colWidths=[103*mm, 45*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (1, -1), (-1, -1), 11),
        ("TEXTCOLOR", (1, -1), (-1, -1), GREEN),
        ("LINEABOVE", (1, -1), (-1, -1), 1, GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)

    story.append(Spacer(1, 8))
    if order.payment_link:
        story.append(Paragraph(
            f"<b>Payment Link:</b> {order.payment_link}", styles["normal"]
        ))
        story.append(Spacer(1, 4))

    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceBefore=6))
    story.append(Paragraph(
        "Thank you for your business! This is a computer generated invoice.",
        styles["center"]
    ))

    doc.build(story)
    return buffer.getvalue()
