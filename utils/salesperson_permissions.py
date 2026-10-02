"""Owner-configurable permissions for named Salesperson accounts."""

import json


PERMISSION_DEFINITIONS = [
    ("view_customer_details", "View customer contact and delivery details", True),
    ("verify_payments", "Verify incoming POS / bank transfers", True),
    ("change_order_status", "Change order status (full status list)", True),
    ("record_weigh_ins", "Record weigh-ins on legacy orders", True),
    ("print_customer_receipts", "Open and print customer receipts", True),
    ("view_customer_settlement", "View final customer balances/refunds on legacy settlement receipts", True),
    ("receive_order_alerts", "Receive new-order push alerts while the shop is open", True),
    ("view_complaints", "View customer complaints", False),
    ("view_inventory", "View product stock summary", False),
]

DEFAULT_PERMISSIONS = {
    key: default_enabled for key, _label, default_enabled in PERMISSION_DEFINITIONS
}


def get_salesperson_permissions(account):
    """Return a complete permission map; missing legacy keys use current defaults."""
    raw = getattr(account, "permissions_json", None)
    try:
        stored = json.loads(raw) if raw else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        stored = {}
    if not isinstance(stored, dict):
        stored = {}
    return {
        key: bool(stored.get(key, default))
        for key, default in DEFAULT_PERMISSIONS.items()
    }


def serialize_salesperson_permissions(selected):
    """Serialize only known keys, writing disabled choices explicitly as false."""
    selected = set(selected or ())
    return json.dumps(
        {key: key in selected for key in DEFAULT_PERMISSIONS},
        separators=(",", ":"),
        sort_keys=True,
    )


def salesperson_has_permission(account, permission):
    return bool(get_salesperson_permissions(account).get(permission, False))
