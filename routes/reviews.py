from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from models import Order, Review, ShopSettings, db
from utils.notifications import normalize_nigerian_phone

reviews_bp = Blueprint("reviews", __name__)
COMPLETED_ORDER_STATUSES = {"Delivered", "Picked up"}


def review_public_url(endpoint):
    path = url_for(endpoint)
    origin = current_app.config.get("PUBLIC_ORIGIN", "").rstrip("/")
    return f"{origin}{path}" if origin else url_for(endpoint, _external=True)


def find_order(order_ref):
    value = (order_ref or "").strip()
    order = Order.query.filter_by(public_id=value).first()
    if order is None and value.isdigit():
        order = Order.query.filter_by(id=int(value)).first()
    return order


@reviews_bp.route("/reviews", methods=["GET", "POST"])
def submit_review():
    if request.method == "POST":
        order_ref = request.form.get("order_ref", "").strip()
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        try:
            rating = int(request.form.get("rating", "0"))
        except (TypeError, ValueError):
            rating = 0

        order = find_order(order_ref)
        if not order or order.status not in COMPLETED_ORDER_STATUSES:
            flash("Enter a valid order reference for an order marked Delivered or Picked up.", "error")
        elif normalize_nigerian_phone(phone) != normalize_nigerian_phone(order.phone):
            flash("The phone number does not match the customer details on that order.", "error")
        elif order.review is not None:
            flash("That order already has a review. Thank you for sharing your experience.", "error")
        elif not customer_name or len(customer_name) > 120 or not phone or len(phone) > 40:
            flash("Enter your name and the phone number used for the order.", "error")
        elif rating not in range(1, 6):
            flash("Choose a star rating from 1 to 5.", "error")
        elif not title or len(title) > 160 or len(body) < 10 or len(body) > 3000:
            flash("Add a short title and a review between 10 and 3,000 characters.", "error")
        elif email and (len(email) > 160 or "@" not in email):
            flash("Enter a valid email address or leave it blank.", "error")
        else:
            settings = ShopSettings.query.get(1)
            review = Review(
                order_id=order.id,
                customer_name=customer_name,
                phone=phone,
                email=email or None,
                rating=rating,
                title=title,
                body=body,
                status="Approved" if settings and settings.reviews_auto_publish else "Pending",
                published_at=datetime.utcnow() if settings and settings.reviews_auto_publish else None,
            )
            db.session.add(review)
            db.session.commit()
            flash("Thank you. Your review is now live." if review.status == "Approved" else "Thank you. Your review has been sent for approval.", "success")
            return redirect(url_for("reviews.testimonials"))
    return render_template("reviews.html", meta_robots="noindex,follow", page_title="Leave a Verified Review | Beamers Farm", social_title="Leave a Verified Review | Beamers Farm", social_description="Share your verified Beamers Farm order experience with customers in Osogbo.", social_url=review_public_url("reviews.submit_review"), canonical_url=review_public_url("reviews.submit_review"))


@reviews_bp.get("/testimonials")
def testimonials():
    reviews = Review.query.filter_by(status="Approved").order_by(
        Review.published_at.desc(), Review.created_at.desc()
    ).all()
    return render_template("testimonials.html", reviews=reviews, page_title="Customer Testimonials | Beamers Farm", social_title="Customer Testimonials | Beamers Farm", social_description="Read verified customer testimonials about Beamers Farm frozen chicken, delivery, and farm pickup in Osogbo.", social_url=review_public_url("reviews.testimonials"), canonical_url=review_public_url("reviews.testimonials"), meta_keywords="Beamers Farm reviews, chicken delivery reviews Osogbo, customer testimonials")
