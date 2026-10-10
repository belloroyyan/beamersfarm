"""Owner inventory summaries derived from current stock and order snapshots."""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from models import Order, OrderFinancialRecord, OrderItem, Product

SHOP_TIMEZONE = ZoneInfo("Africa/Lagos")
PERIOD_LABELS = {
    "today": "Today",
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "month": "This month",
    "year": "This year",
    "all": "All time",
    "custom": "Custom range",
}


def _utc_naive_midnight(local_day):
    return datetime.combine(local_day, time.min, tzinfo=SHOP_TIMEZONE).astimezone(
        timezone.utc
    ).replace(tzinfo=None)


def build_inventory_report(period="30d", search="", start_raw="", end_raw="", now=None):
    """Build the report; order timeframe boundaries are interpreted in Africa/Lagos."""
    now_local = now.astimezone(SHOP_TIMEZONE) if now else datetime.now(SHOP_TIMEZONE)
    today = now_local.date()
    period = period if period in PERIOD_LABELS else "30d"
    start_day = end_day = None

    if period == "today":
        start_day = end_day = today
    elif period == "7d":
        start_day, end_day = today - timedelta(days=6), today
    elif period == "30d":
        start_day, end_day = today - timedelta(days=29), today
    elif period == "month":
        start_day, end_day = today.replace(day=1), today
    elif period == "year":
        start_day, end_day = today.replace(month=1, day=1), today
    elif period == "custom":
        try:
            start_day = date.fromisoformat(start_raw)
            end_day = date.fromisoformat(end_raw)
            if end_day < start_day:
                raise ValueError("End date must be on or after the start date.")
        except (TypeError, ValueError) as exc:
            raise ValueError("Choose valid start and end dates for the custom range.") from exc

    start_at = _utc_naive_midnight(start_day) if start_day else None
    end_at = _utc_naive_midnight(end_day + timedelta(days=1)) if end_day else None
    orders_query = Order.query.options(
        selectinload(Order.items),
        selectinload(Order.financial_records),
    )
    if start_at is not None:
        orders_query = orders_query.filter(Order.created_at >= start_at)
    if end_at is not None:
        orders_query = orders_query.filter(Order.created_at < end_at)
    orders = orders_query.all()

    # Cash/transfer receipts are measured by when they were actually settled,
    # not when the customer originally placed the order.
    money_received = Decimal("0.00")
    money_refunded = Decimal("0.00")
    financial_query = OrderFinancialRecord.query.filter_by(status="settled")
    settlement_at = func.coalesce(
        OrderFinancialRecord.settled_at, OrderFinancialRecord.created_at
    )
    if start_at is not None:
        financial_query = financial_query.filter(settlement_at >= start_at)
    if end_at is not None:
        financial_query = financial_query.filter(settlement_at < end_at)
    for record in financial_query.all():
        amount = Decimal(str(record.amount or 0))
        if record.event_type in {"initial_payment", "balance_payment"}:
            money_received += amount
        elif record.event_type == "refund":
            money_refunded += amount

    products = Product.query.order_by(Product.name.asc(), Product.id.asc()).all()
    product_by_id = {product.id: product for product in products}
    rows_by_key = {}
    for product in products:
        rows_by_key[("product", product.id)] = {
            "product_id": product.id,
            "name": product.name,
            "unit": product.unit,
            "stock": product.stock,
            "active": product.active,
            "verified_units": Decimal("0.000"),
            "pending_units": Decimal("0.000"),
            "cancelled_units": Decimal("0.000"),
            "verified_requested_kg": Decimal("0.000"),
            "pending_requested_kg": Decimal("0.000"),
            "verified_sales": Decimal("0.00"),
        }

    verified_order_ids = set()
    pending_order_ids = set()
    cancelled_order_ids = set()
    for order in orders:
        for item in order.items:
            product = product_by_id.get(item.product_id)
            key = ("product", item.product_id) if product else ("orphan", item.product_name)
            row = rows_by_key.get(key)
            if row is None:
                row = {
                    "product_id": item.product_id,
                    "name": item.product_name,
                    "unit": item.unit or "unit",
                    "stock": 0,
                    "active": False,
                    "verified_units": Decimal("0.000"),
                    "pending_units": Decimal("0.000"),
                    "cancelled_units": Decimal("0.000"),
                    "verified_requested_kg": Decimal("0.000"),
                    "pending_requested_kg": Decimal("0.000"),
                    "verified_sales": Decimal("0.00"),
                }
                rows_by_key[key] = row

            quantity = Decimal(str(item.quantity or 0))
            requested_kg = item.requested_weight_kg
            if requested_kg is None:
                requested_kg = item.actual_weight_kg
            requested_kg = Decimal(str(requested_kg or 0))
            if order.status == "Cancelled":
                row["cancelled_units"] += quantity
                cancelled_order_ids.add(order.id)
            elif order.payment_status == "Verified":
                row["verified_units"] += quantity
                row["verified_requested_kg"] += requested_kg
                line_total = item.final_subtotal if item.pricing_type == "weight_deposit" and item.actual_weight_kg is not None else item.subtotal
                row["verified_sales"] += Decimal(str(line_total or 0))
                verified_order_ids.add(order.id)
            else:
                row["pending_units"] += quantity
                row["pending_requested_kg"] += requested_kg
                pending_order_ids.add(order.id)

    all_rows = sorted(rows_by_key.values(), key=lambda row: (row["name"].casefold(), row["product_id"] or 0))
    search = (search or "").strip()[:120]
    if search:
        lowered = search.casefold()
        numeric_id = int(search) if search.isdigit() else None
        visible_rows = [
            row for row in all_rows
            if (numeric_id is not None and row["product_id"] == numeric_id)
            or lowered in row["name"].casefold()
        ]
    else:
        visible_rows = all_rows

    if period == "all":
        period_label = "All time"
    else:
        range_label = f"{start_day:%d %b %Y} – {end_day:%d %b %Y}"
        period_label = f"{PERIOD_LABELS[period]} · {range_label}"

    return {
        "period": period,
        "period_label": period_label,
        "start_date": start_day.isoformat() if start_day else "",
        "end_date": end_day.isoformat() if end_day else "",
        "search_query": search,
        "rows": visible_rows,
        "orders": orders,
        "metrics": {
            "active_stock_units": sum((Decimal(str(product.stock or 0)) for product in products if product.active), Decimal("0.000")),
            "low_stock_products": sum(1 for product in products if product.active and product.stock <= product.low_stock_threshold),
            "verified_orders": len(verified_order_ids),
            "pending_orders": len(pending_order_ids),
            "cancelled_orders": len(cancelled_order_ids),
            "verified_units": sum((row["verified_units"] for row in all_rows), Decimal("0.000")),
            "pending_units": sum((row["pending_units"] for row in all_rows), Decimal("0.000")),
            "cancelled_units": sum((row["cancelled_units"] for row in all_rows), Decimal("0.000")),
            "verified_item_sales": sum((row["verified_sales"] for row in all_rows), Decimal("0.00")),
            "money_received": money_received,
            "money_refunded": money_refunded,
            "net_cash_inflow": money_received - money_refunded,
        },
        "products_total": len(products),
        "lines_total": len(all_rows),
    }
