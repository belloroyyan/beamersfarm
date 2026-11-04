import hmac
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from models import ShopSettings, Order, Review, db
from utils.notifications import normalize_nigerian_phone
from utils.order_workflow import ORDER_STATUSES
from utils.review_media import save_review_image

reviews_bp = Blueprint("reviews", __name__)
REVIEW_ELIGIBLE_STATUSES = set(ORDER_STATUSES) - {"Cancelled"}


def review_public_url(endpoint):
    path = url_for(endpoint)
    origin = current_app.config.get("PUBLIC_ORIGIN", "").rstrip("/")
    return f"{origin}{path}" if origin else path


def find_order(order_uuid):
    value = (order_uuid or "").strip()
    if not value or len(value) > 80:
        return None
    return Order.query.filter_by(public_id=value).first()


def _review_template():
    endpoint_url = review_public_url("reviews.submit_review")
    return render_template(
        "reviews.html", meta_robots="noindex,follow",
        page_title="Leave a Verified Review | Beamers Farms",
        social_title="Leave a Verified Review | Beamers Farms",
        social_description="Share your verified Beamers Farms order experience with customers in Osogbo.",
        social_url=endpoint_url, canonical_url=endpoint_url,
    )


@reviews_bp.route("/reviews", methods=["GET", "POST"])
def submit_review():
    settings = ShopSettings.query.get(1)
    if settings and not settings.reviews_open:
        flash("Reviews are temporarily closed.", "error")
        return redirect(url_for("shop.index"))
    if request.method == "POST":
        quick_review = request.form.get("quick_review") == "1"
        order_uuid = request.form.get("order_uuid") or request.form.get("order_ref", "")
        order = find_order(order_uuid)
        order_token = request.form.get("order_token", "")
        if quick_review and order and not hmac.compare_digest(order.public_token or "", order_token):
            order = None
        customer_name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        review_image, image_error = save_review_image(request.files.get("image"))
        try:
            rating = int(request.form.get("rating", "0"))
        except (TypeError, ValueError):
            rating = 0
        error_message = image_error
        if error_message is None:
            if not order:
                error_message = "Enter a valid public order UUID."
            elif order.status not in REVIEW_ELIGIBLE_STATUSES:
                error_message = "That order is not eligible for a review yet. The order must be Received or later and must not be cancelled."
            elif normalize_nigerian_phone(phone) != normalize_nigerian_phone(order.phone):
                error_message = "The phone number does not match the customer details on that order."
            elif order.review is not None:
                error_message = "That order already has a review. Thank you for sharing your experience."
            elif not customer_name or len(customer_name) > 120 or not phone or len(phone) > 40:
                error_message = "Enter your name and the phone number used for the order."
            elif rating not in range(1, 6):
                error_message = "Choose a star rating from 1 to 5."
            elif quick_review:
                title = f"{rating}-star order rating"
                body = body[:1000] or f"The customer rated this Beamers Farms order {rating} out of 5 stars."
            elif not title or len(title) > 160 or len(body) < 10 or len(body) > 3000:
                error_message = "Add a short title and a review between 10 and 3,000 characters."
            elif email and (len(email) > 160 or "@" not in email):
                error_message = "Enter a valid email address or leave it blank."
        if error_message:
            flash(error_message, "error")
            if quick_review and order and hmac.compare_digest(order.public_token or "", order_token):
                return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
        else:
            settings = ShopSettings.query.get(1)
            review = Review(
                order_id=order.id, customer_name=customer_name, phone=phone,
                email=email or None, rating=rating, title=title, body=body,
                image=review_image,
                status="Approved" if settings and settings.reviews_auto_publish else "Pending",
                published_at=datetime.utcnow() if settings and settings.reviews_auto_publish else None,
            )
            db.session.add(review)
            db.session.commit()
            flash("Thank you. Your review is now live." if review.status == "Approved" else "Thank you. Your review has been sent for approval.", "success")
            if quick_review:
                return redirect(url_for("shop.order_success", order_ref=order.public_id, token=order.public_token))
            return redirect(url_for("reviews.testimonials"))
    return _review_template()


@reviews_bp.get("/testimonials")
def testimonials():
    reviews = Review.query.filter_by(status="Approved").order_by(Review.published_at.desc(), Review.created_at.desc()).all()
    return render_template(
        "testimonials.html", reviews=reviews,
        page_title="Customer Testimonials | Beamers Farms",
        social_title="Customer Testimonials | Beamers Farms",
        social_description="Read verified customer testimonials about Beamers Farms frozen chicken, delivery, and farm pickup in Osogbo.",
        social_url=review_public_url("reviews.testimonials"),
        canonical_url=review_public_url("reviews.testimonials"),
        meta_keywords="Beamers Farms reviews, chicken delivery reviews Osogbo, customer testimonials",
    )
