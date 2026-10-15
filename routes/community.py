from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from models import (
    CommunityBlock, CommunityComment, CommunityNotification, CommunityPost,
    CommunityReaction, CommunityReport, Customer, CustomerNotice, Product,
    ShopSettings, db,
)
from routes.customer import current_customer
from utils.community_media import community_image_url, save_community_image
from utils.web_push import send_customer_community_reply_push

community_bp = Blueprint("community", __name__, url_prefix="/community")
CATEGORIES = ["Everything", "Order help", "Little notes", "Ideas & feedback"]
REPORT_REASONS = ["Spam", "Abusive or hateful", "Inappropriate content", "Something else"]


def signed_customer():
    customer = current_customer()
    return customer if customer and customer.active else None


def require_customer():
    customer = signed_customer()
    if not customer:
        flash("Sign in to join the community conversation.", "error")
        return None
    if customer.community_posting_blocked:
        flash("Your community posting access is paused. You can still read public conversations.", "error")
        return None
    return customer


def write_redirect():
    if signed_customer():
        return redirect(url_for("community.feed"))
    return redirect(url_for("customer.login", next=url_for("community.feed")))


def staff():
    return session.get("staff_role") == "owner" or session.get("admin_logged_in")


def community_write_guard():
    settings = ShopSettings.query.get(1)
    if settings and not settings.community_open:
        flash(settings.community_closed_message, "error")
        return False
    return True


def _community_author_names(posts, comments):
    customer_ids = {post.customer_id for post in posts if post.customer_id}
    customer_ids.update(comment.customer_id for thread in comments.values() for comment in thread if comment.customer_id)
    people = {person.id: person for person in Customer.query.filter(Customer.id.in_(customer_ids)).all()} if customer_ids else {}

    def visible_name(customer_id, fallback="Community member"):
        person = people.get(customer_id)
        return person.name if person and person.community_profile_public and person.active else fallback

    post_names = {post.id: visible_name(post.customer_id) for post in posts}
    comment_names = {
        comment.id: ("Beamers Farm team" if comment.is_staff else visible_name(comment.customer_id))
        for thread in comments.values() for comment in thread
    }
    return post_names, comment_names


@community_bp.get("/")
def feed():
    customer = signed_customer()
    category = request.args.get("category", "Everything")
    search_query = request.args.get("q", "").strip()[:120]
    is_profile_search = search_query.startswith("@")
    blocked = {
        row.blocked_customer_id
        for row in CommunityBlock.query.filter_by(blocker_customer_id=customer.id).all()
    } if customer else set()

    public_profiles = []
    if is_profile_search:
        term = search_query[1:].strip()[:110]
        if term:
            pattern = f"%{term}%"
            public_profiles = Customer.query.filter(
                Customer.active.is_(True),
                Customer.deleted_at.is_(None),
                Customer.community_profile_public.is_(True),
                or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern), Customer.email.ilike(pattern)),
            ).order_by(Customer.name.asc()).limit(30).all()
        posts = []
    else:
        query = CommunityPost.query.filter_by(status="published")
        if category in CATEGORIES[1:]:
            query = query.filter_by(category=category)
        if search_query:
            pattern = f"%{search_query}%"
            matching_comment_post_ids = db.session.query(CommunityComment.post_id).filter(
                CommunityComment.status == "published",
                CommunityComment.body.ilike(pattern),
            )
            query = query.filter(or_(CommunityPost.body.ilike(pattern), CommunityPost.id.in_(matching_comment_post_ids)))
        posts = query.order_by(CommunityPost.created_at.desc()).limit(100).all()
        posts = [post for post in posts if post.customer_id not in blocked]

    comments = {}
    reactions = {}
    for post in posts:
        comments[post.id] = CommunityComment.query.filter_by(post_id=post.id, status="published").order_by(CommunityComment.created_at.asc()).all()
        reactions[post.id] = CommunityReaction.query.filter_by(post_id=post.id).count()
    post_authors, comment_authors = _community_author_names(posts, comments)
    unread = CommunityNotification.query.filter_by(customer_id=customer.id, read_at=None).count() if customer else 0
    settings = ShopSettings.query.get(1)

    popular_posts = sorted(posts, key=lambda post: (reactions.get(post.id, 0) + len(comments.get(post.id, [])), post.created_at), reverse=True)[:3]
    recently_answered = []
    for post in posts:
        staff_replies = [comment for comment in comments.get(post.id, []) if comment.is_staff]
        if staff_replies:
            recently_answered.append((post, max(staff_replies, key=lambda comment: comment.created_at)))
    recently_answered.sort(key=lambda row: row[1].created_at, reverse=True)

    product_mentions = []
    searchable_text = "\n".join(post.body.casefold() for post in CommunityPost.query.filter_by(status="published").all())
    for product in Product.query.filter_by(active=True).order_by(Product.name.asc()).all():
        count = searchable_text.count(product.name.casefold()) if product.name else 0
        if count:
            product_mentions.append((product, count))
    product_mentions.sort(key=lambda row: (-row[1], row[0].name.casefold()))

    considered_suggestions = CommunityPost.query.filter_by(
        status="published", considering=True, category="Ideas & feedback"
    ).order_by(CommunityPost.updated_at.desc()).limit(4).all()
    considered_names, _ = _community_author_names(considered_suggestions, {})

    return render_template(
        "community/feed.html",
        posts=posts,
        comments=comments,
        reactions=reactions,
        categories=CATEGORIES,
        selected_category=category,
        search_query=search_query,
        is_profile_search=is_profile_search,
        public_profiles=public_profiles,
        customer=customer,
        unread_notifications=unread,
        post_authors=post_authors,
        comment_authors=comment_authors,
        popular_posts=popular_posts,
        recently_answered=recently_answered[:4],
        product_mentions=product_mentions[:5],
        considered_suggestions=considered_suggestions,
        considered_names=considered_names,
        community_image_url=community_image_url,
        community_open=settings.community_open if settings else True,
        community_closed_message=settings.community_closed_message if settings else "The community is currently closed.",
        community_blocked=bool(customer and customer.community_posting_blocked),
    )


@community_bp.post("/posts")
def create_post():
    customer = require_customer()
    if not customer:
        return write_redirect()
    if not community_write_guard():
        return redirect(url_for("community.feed"))
    body = request.form.get("body", "").strip()
    category = request.form.get("category", "").strip()
    if category not in CATEGORIES[1:] and category != "":
        category = ""
    if not body or len(body) > 4000:
        flash("Write a post up to 4,000 characters.", "error")
        return redirect(url_for("community.feed"))
    image, error = save_community_image(request.files.get("image"))
    if error:
        flash(error, "error")
        return redirect(url_for("community.feed"))
    db.session.add(CommunityPost(
        customer_id=customer.id,
        author_name=customer.name if customer.community_profile_public else "Community member",
        category=category,
        body=body,
        image=image,
    ))
    db.session.commit()
    flash("Your post is now in the community.", "success")
    return redirect(url_for("community.feed"))


@community_bp.post("/posts/<int:post_id>/comments")
def add_comment(post_id):
    customer = require_customer()
    if not customer:
        return write_redirect()
    if not community_write_guard():
        return redirect(url_for("community.feed"))
    post = CommunityPost.query.filter_by(id=post_id, status="published").first_or_404()
    body = request.form.get("body", "").strip()
    if not body or len(body) > 2000:
        flash("Write a reply up to 2,000 characters.", "error")
        return redirect(url_for("community.feed"))
    db.session.add(CommunityComment(post_id=post.id, customer_id=customer.id, author_name=customer.name if customer.community_profile_public else "Community member", body=body))
    db.session.commit()
    return redirect(url_for("community.feed"))


@community_bp.post("/posts/<int:post_id>/react")
def react(post_id):
    customer = require_customer()
    if not customer:
        return write_redirect()
    if not community_write_guard():
        return redirect(url_for("community.feed"))
    post = CommunityPost.query.filter_by(id=post_id, status="published").first_or_404()
    existing = CommunityReaction.query.filter_by(post_id=post.id, customer_id=customer.id).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(CommunityReaction(post_id=post.id, customer_id=customer.id))
    db.session.commit()
    return redirect(url_for("community.feed"))


@community_bp.post("/posts/<int:post_id>/edit")
def edit_post(post_id):
    customer = require_customer()
    post = CommunityPost.query.get_or_404(post_id)
    if not customer:
        return write_redirect()
    if post.customer_id != customer.id:
        abort(403)
    body = request.form.get("body", "").strip()
    if not body or len(body) > 4000:
        flash("Post text is required and must be under 4,000 characters.", "error")
    else:
        post.body = body
        post.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Post updated.", "success")
    return redirect(url_for("community.feed"))


@community_bp.post("/posts/<int:post_id>/delete")
def delete_post(post_id):
    customer = require_customer()
    post = CommunityPost.query.get_or_404(post_id)
    if not customer:
        return write_redirect()
    if post.customer_id != customer.id:
        abort(403)
    post.status = "deleted"
    db.session.commit()
    flash("Your post was removed.", "success")
    return redirect(url_for("community.feed"))


@community_bp.post("/comments/<int:comment_id>/edit")
def edit_comment(comment_id):
    customer = require_customer()
    comment = CommunityComment.query.get_or_404(comment_id)
    if not customer:
        return write_redirect()
    if comment.customer_id != customer.id:
        abort(403)
    body = request.form.get("body", "").strip()
    if body and len(body) <= 2000:
        comment.body = body
        comment.updated_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("community.feed"))


@community_bp.post("/comments/<int:comment_id>/delete")
def delete_comment(comment_id):
    customer = require_customer()
    comment = CommunityComment.query.get_or_404(comment_id)
    if not customer:
        return write_redirect()
    if comment.customer_id != customer.id:
        abort(403)
    comment.status = "deleted"
    db.session.commit()
    return redirect(url_for("community.feed"))


@community_bp.post("/posts/<int:post_id>/report")
def report_post(post_id):
    customer = require_customer()
    post = CommunityPost.query.filter_by(id=post_id, status="published").first_or_404()
    if not customer:
        return write_redirect()
    reason = request.form.get("reason", "Something else")
    db.session.add(CommunityReport(post_id=post.id, reporter_customer_id=customer.id, reason=reason if reason in REPORT_REASONS else REPORT_REASONS[-1]))
    db.session.commit()
    flash("Thank you. The community team will review this report.", "success")
    return redirect(url_for("community.feed"))


@community_bp.post("/customers/<int:customer_id>/block")
def block_customer(customer_id):
    customer = require_customer()
    if not customer or customer.id == customer_id:
        return write_redirect()
    if not CommunityBlock.query.filter_by(blocker_customer_id=customer.id, blocked_customer_id=customer_id).first():
        db.session.add(CommunityBlock(blocker_customer_id=customer.id, blocked_customer_id=customer_id))
        db.session.commit()
    flash("That member's posts are now hidden from your feed.", "success")
    return redirect(url_for("community.feed"))


@community_bp.get("/notifications")
def notifications():
    customer = signed_customer()
    if not customer:
        return redirect(url_for("customer.login"))
    items = CommunityNotification.query.filter_by(customer_id=customer.id).order_by(CommunityNotification.created_at.desc()).limit(50).all()
    now = datetime.utcnow()
    for item in items:
        item.read_at = item.read_at or now
    db.session.commit()
    return render_template("community/notifications.html", notifications=items)


@community_bp.post("/posts/<int:post_id>/staff-reply")
def staff_reply(post_id):
    if not staff():
        abort(403)
    post = CommunityPost.query.get_or_404(post_id)
    body = request.form.get("body", "").strip()
    if not body or len(body) > 2000:
        return redirect(url_for("community.support"))
    db.session.add(CommunityComment(post_id=post.id, author_name="Beamers Farm team", body=body, is_staff=True))
    if post.customer_id:
        db.session.add(CommunityNotification(customer_id=post.customer_id, post_id=post.id, message="Beamers Farm replied to your community post."))
        db.session.add(CustomerNotice(customer_id=post.customer_id, title="A community reply from Beamers Farm", message="The Beamers Farm team replied to your community conversation.", kind="community"))
    db.session.commit()
    if post.customer_id:
        customer = db.session.get(Customer, post.customer_id)
        send_customer_community_reply_push(customer, post)
    return redirect(url_for("community.support"))


@community_bp.route("/support", methods=["GET", "POST"])
def support():
    if not staff():
        abort(403)
    settings = ShopSettings.query.get(1)
    if request.method == "POST":
        if request.form.get("action") == "toggle":
            settings.community_open = not settings.community_open
        elif request.form.get("action") == "message":
            settings.community_closed_message = request.form.get("closed_message", "").strip()[:500] or settings.community_closed_message
        db.session.commit()
        flash("Community settings saved.", "success")
        return redirect(url_for("community.support"))
    posts = CommunityPost.query.filter_by(status="published").order_by(CommunityPost.created_at.desc()).limit(100).all()
    unanswered = [post for post in posts if not CommunityComment.query.filter_by(post_id=post.id, is_staff=True, status="published").first()]
    reports = CommunityReport.query.filter_by(status="open").order_by(CommunityReport.created_at.desc()).all()
    comments = {post.id: CommunityComment.query.filter_by(post_id=post.id, status="published").all() for post in posts}
    author_names, _ = _community_author_names(posts, comments)
    return render_template("admin/community_support.html", unanswered=unanswered, reports=reports, comments=comments, author_names=author_names, community_settings=settings, suggestions=[post for post in posts if post.category == "Ideas & feedback"])


@community_bp.post("/posts/<int:post_id>/considering")
def toggle_suggestion_considering(post_id):
    if not staff():
        abort(403)
    post = CommunityPost.query.get_or_404(post_id)
    post.considering = not post.considering
    post.updated_at = datetime.utcnow()
    if post.customer_id:
        message = "Beamers Farm is considering your suggestion." if post.considering else "Beamers Farm updated the review status of your suggestion."
        db.session.add(CustomerNotice(customer_id=post.customer_id, title="Suggestion status updated", message=message, kind="community"))
    db.session.commit()
    flash("Suggestion status updated.", "success")
    return redirect(url_for("community.support"))


@community_bp.post("/moderation/reports/<int:report_id>")
def moderate_report(report_id):
    if not staff():
        abort(403)
    report = CommunityReport.query.get_or_404(report_id)
    action = request.form.get("action")
    report.status = "resolved"
    affected_customer_id = None
    if action == "hide" and report.post_id:
        post = db.session.get(CommunityPost, report.post_id)
        if post:
            post.status = "hidden"
            affected_customer_id = post.customer_id
    if action == "hide-comment" and report.comment_id:
        comment = db.session.get(CommunityComment, report.comment_id)
        if comment:
            comment.status = "hidden"
            affected_customer_id = comment.customer_id
    if affected_customer_id:
        db.session.add(CustomerNotice(customer_id=affected_customer_id, title="A community post was moderated", message="The Beamers Farm team reviewed community content connected to your account. Please keep future posts respectful and helpful.", kind="community"))
    db.session.commit()
    return redirect(url_for("community.support"))
