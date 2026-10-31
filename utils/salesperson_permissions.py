"""Owner-configurable permissions for named Salesperson accounts."""

import json


PERMISSION_DEFINITIONS = [
    # Order desk
    ("view_order_stream", "View the live order stream", True),
    ("view_customer_details", "View customer contact and delivery details", True),
    ("verify_payments", "Verify incoming POS / bank transfers", True),
    ("change_order_status", "Change order status (full status list)", True),
    ("record_weigh_ins", "Record weigh-ins on legacy orders", True),
    ("print_customer_receipts", "Open and print customer receipts", True),
    ("view_customer_settlement", "View final customer balances/refunds on legacy settlement receipts", True),
    # Customer care
    ("view_complaints", "View customer complaints", True),
    ("manage_complaints", "Manage complaints: update status and add notes", True),
    ("manage_community", "Moderate community posts, reports and suggestions", False),
    # Counter and stock
    ("record_in_person_orders", "Record cash/POS orders at the farm counter", False),
    ("view_inventory", "View product stock summary", False),
    # Alerts
    ("receive_order_alerts", "Receive new-order push alerts while the shop is open", True),
]

# Used by the owner's Staff access page to show the checkboxes in sections.
PERMISSION_GROUPS = [
    ("Order desk", ["view_order_stream", "view_customer_details", "verify_payments", "change_order_status",
                    "record_weigh_ins", "print_customer_receipts", "view_customer_settlement"]),
    ("Customer care", ["view_complaints", "manage_complaints", "manage_community"]),
    ("Counter and stock", ["record_in_person_orders", "view_inventory"]),
    ("Alerts", ["receive_order_alerts"]),
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
