from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import Complaint, Order, ShopSettings, db
from utils.web_push import send_owner_complaint_push

complaints_bp = Blueprint("complaints", __name__)
COMPLAINT_CATEGORIES = [
    "Late delivery",
    "Missing item",
    "Incorrect item",
    "Product quality",
    "Payment issue",
    "Delivery experience",
    "Other",
]


@complaints_bp.route("/complaint", methods=["GET", "POST"])
def create_complaint():
    settings = ShopSettings.query.get(1)
    if settings and not settings.customer_care_open:
        flash("Customer care is temporarily unavailable. Please try again later.", "error")
        return redirect(url_for("shop.index"))
    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "").strip()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()
        order_number = request.form.get("order_number", "").strip()
        order = None
        if order_number:
            order = Order.query.filter_by(public_id=order_number.strip()).first()
            if order is None and order_number.isdigit():
                order = db.session.get(Order, int(order_number))
            if order and "".join(ch for ch in phone if ch.isdigit())[-10:] != "".join(ch for ch in order.phone if ch.isdigit())[-10:]:
                order = None
        if (
            not name or len(name) > 120 or not phone or len(phone) > 40
            or category not in COMPLAINT_CATEGORIES or not subject or len(subject) > 160
            or len(description) < 10 or len(description) > 5000
        ):
            flash("Please complete the form with a short subject and at least 10 characters describing the issue.", "error")
            return render_template("complaints/new.html", categories=COMPLAINT_CATEGORIES)
        complaint = Complaint(
            order=order, customer_name=name, phone=phone, category=category,
            subject=subject, description=description,
        )
        db.session.add(complaint)
        db.session.commit()
        send_owner_complaint_push(complaint)
        return render_template("complaints/received.html", name=name)
    return render_template("complaints/new.html", categories=COMPLAINT_CATEGORIES)
