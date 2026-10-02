"""Render owner inventory summaries as a branded, vector-watermarked PDF."""

from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor("#23382f")
LIME = colors.HexColor("#d4e88f")
MUTED = colors.HexColor("#68776f")


def _amount(value):
    return f"NGN {Decimal(str(value or 0)):,.2f}"


def build_inventory_pdf(report, brand_mark_path=None):
    """Return a complete A4 landscape inventory-summary PDF as bytes."""
    from io import BytesIO

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=11 * mm,
        rightMargin=11 * mm,
        topMargin=14 * mm,
        bottomMargin=13 * mm,
        title="Beamers Farm Inventory Summary",
        author="Beamers Farm",
        subject=report["period_label"],
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="FarmTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=23, textColor=INK, alignment=TA_LEFT, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="FarmSubtitle", parent=styles["Normal"], fontSize=9, leading=12,
        textColor=MUTED, spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        name="Cell", parent=styles["Normal"], fontSize=7.2, leading=9,
        textColor=INK, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="CellRight", parent=styles["Cell"], alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        name="CellHead", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7, leading=8, textColor=colors.white, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="MetricLabel", parent=styles["Normal"], fontSize=7.5,
        textColor=MUTED, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="MetricValue", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10.5, leading=13, textColor=INK, alignment=TA_CENTER,
    ))
    story = []

    title_block = [
        Paragraph("INVENTORY SUMMARY", styles["FarmTitle"]),
        Paragraph(f"Reporting period: {escape(report['period_label'])}", styles["FarmSubtitle"]),
        Paragraph("Gross item values are from verified, non-cancelled orders placed in this period, before recorded refunds and excluding delivery fees. Money received/refunded uses actual settled transaction timestamps. Product stock is the current count of sale units.", styles["FarmSubtitle"]),
    ]
    if report.get("search_query"):
        title_block.append(Paragraph(f"Table filter: {escape(report['search_query'])} (summary figures below cover all products)", styles["FarmSubtitle"]))
    if brand_mark_path:
        try:
            logo = Image(brand_mark_path, width=17 * mm, height=17 * mm, kind="proportional")
            header = Table([[logo, title_block]], colWidths=[21 * mm, 245 * mm])
            header.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(header)
        except (OSError, ValueError):
            story.extend(title_block)
    else:
        story.extend(title_block)
    story.append(Spacer(1, 6 * mm))

    metrics = report["metrics"]
    metric_cells = []
    for label, value in [
        ("ACTIVE STOCK UNITS", f"{metrics['active_stock_units']:,}"),
        ("LOW-STOCK PRODUCTS", f"{metrics['low_stock_products']:,}"),
        ("VERIFIED ORDERS", f"{metrics['verified_orders']:,}"),
        ("GROSS ITEM SALES", _amount(metrics["verified_item_sales"])),
        ("MONEY RECEIVED", _amount(metrics["money_received"])),
        ("NET CASH INFLOW", _amount(metrics["net_cash_inflow"])),
    ]:
        metric_cells.append([
            Paragraph(label, styles["MetricLabel"]),
            Paragraph(escape(value), styles["MetricValue"]),
        ])
    metric_table = Table([metric_cells], colWidths=[doc.width / len(metric_cells)] * len(metric_cells))
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7f1")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dfe6dc")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dfe6dc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 5 * mm))

    headers = ["Product ID", "Product", "Catalog", "On hand", "Verified units", "Unverified reserved", "Cancelled", "Verified kg", "Gross item sales (NGN)"]
    table_data = [[Paragraph(escape(label), styles["CellHead"]) for label in headers]]
    for row in report["rows"]:
        product_id = f"#{row['product_id']}" if row["product_id"] is not None else "—"
        catalog_status = "Active" if row["active"] else ("Archived" if row["product_id"] is not None else "Removed")
        table_data.append([
            Paragraph(escape(product_id), styles["Cell"]),
            Paragraph(escape(row["name"]), styles["Cell"]),
            Paragraph(catalog_status, styles["Cell"]),
            Paragraph(f"{row['stock']:,}", styles["CellRight"]),
            Paragraph(f"{row['verified_units']:,}", styles["CellRight"]),
            Paragraph(f"{row['pending_units']:,}", styles["CellRight"]),
            Paragraph(f"{row['cancelled_units']:,}", styles["CellRight"]),
            Paragraph(f"{row['verified_requested_kg']:,.3f}", styles["CellRight"]),
            Paragraph(_amount(row["verified_sales"]), styles["CellRight"]),
        ])
    if not report["rows"]:
        table_data.append([Paragraph("No product rows match this search.", styles["Cell"])] + [""] * (len(headers) - 1))
    table = Table(
        table_data,
        colWidths=[20 * mm, 48 * mm, 19 * mm, 20 * mm, 23 * mm, 29 * mm, 20 * mm, 22 * mm, 31 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8faf6")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce4da")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    note = (
        f"Also in this period: {metrics['pending_orders']:,} unverified order(s) reserve "
        f"{metrics['pending_units']:,} unit(s); {metrics['cancelled_orders']:,} cancelled "
        f"order(s) returned {metrics['cancelled_units']:,} unit(s) to stock. "
        f"Gross item values are before recorded refunds and exclude delivery fees. Actual settled refunds: {_amount(metrics['money_refunded'])}; net cash inflow after refunds: {_amount(metrics['net_cash_inflow'])}. Stock is counted in physical sale units (birds, packs, etc.); kg values are customer-requested totals on verified lines."
    )
    story.append(Paragraph(escape(note), styles["FarmSubtitle"]))

    def draw_page(canvas, document):
        width, height = landscape(A4)
        canvas.saveState()
        # Fine vector diagonals form a light geometric background watermark.
        canvas.setStrokeColor(colors.Color(0.14, 0.22, 0.18, alpha=0.035))
        canvas.setLineWidth(0.35)
        step = 17 * mm
        offset = -height
        while offset < width:
            canvas.line(offset, 0, offset + height, height)
            offset += step
        # Large brand-neutral report watermark behind the printed content.
        canvas.saveState()
        canvas.translate(width / 2, height / 2)
        canvas.rotate(28)
        canvas.setFillColor(colors.Color(0.14, 0.22, 0.18, alpha=0.055))
        canvas.setFont("Helvetica-Bold", 31)
        canvas.drawCentredString(0, 0, "BEAMERS FARM  ·  INVENTORY")
        canvas.restoreState()
        canvas.setStrokeColor(LIME)
        canvas.setLineWidth(2)
        canvas.line(11 * mm, 9 * mm, width - 11 * mm, 9 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(11 * mm, 5 * mm, "Private owner report · Generated from current order and stock records")
        canvas.drawRightString(width - 11 * mm, 5 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()
