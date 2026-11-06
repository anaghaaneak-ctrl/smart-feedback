"""Smart Feedback Collection & Analysis System - Flask REST backend."""
import os
import re
import secrets
from collections import Counter
from functools import wraps
from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import func
from werkzeug.security import check_password_hash

from models import db, Product, Order, Feedback, ORDER_STAGES
from sentiment import analyze

load_dotenv()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CATEGORIES = ["General", "Product", "Delivery", "Service", "Website"]


def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///feedback.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME")
    app.config["ADMIN_PASSWORD_HASH"] = os.getenv("ADMIN_PASSWORD_HASH")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if config:
        app.config.update(config)
    if not os.getenv("SECRET_KEY") and not (config and config.get("SECRET_KEY")):
        app.logger.warning("SECRET_KEY is unset; sessions will be invalidated when the app restarts.")
    CORS(app)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_if_empty()
    register_routes(app)
    return app


def err(msg, code=400):
    return jsonify({"error": msg}), code


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("admin_logged_in") is True:
            return view(*args, **kwargs)
        if request.path.startswith("/api/"):
            return err("Admin authentication required", 401)
        return redirect(url_for("admin_login"))
    return wrapped


def seed_if_empty():
    if Product.query.count() == 0:
        db.session.add_all([
            Product(name="Wireless Earbuds", price=49.99, stock=25),
            Product(name="Smart Watch", price=129.00, stock=10),
            Product(name="Laptop Stand", price=29.50, stock=0),
        ])
        db.session.commit()


# ---------------- validation ----------------
def validate_feedback(d, partial=False):
    errors = {}
    if not partial or "name" in d:
        if not str(d.get("name", "")).strip() or len(str(d.get("name"))) > 120:
            errors["name"] = "Name is required (max 120 chars)."
    if not partial or "email" in d:
        if not EMAIL_RE.match(str(d.get("email", ""))):
            errors["email"] = "Valid email is required."
    if not partial or "rating" in d:
        try:
            if not 1 <= int(d.get("rating")) <= 5:
                raise ValueError
        except (TypeError, ValueError):
            errors["rating"] = "Rating must be 1-5."
    if not partial or "message" in d:
        m = str(d.get("message", "")).strip()
        if len(m) < 5 or len(m) > 2000:
            errors["message"] = "Message must be 5-2000 characters."
    if "category" in d and d["category"] not in CATEGORIES:
        errors["category"] = f"Category must be one of {CATEGORIES}."
    return errors


def register_routes(app):
    # ---------------- pages ----------------
    @app.get("/")
    def home():
        return render_template("index.html", categories=CATEGORIES)

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if session.get("admin_logged_in") is True:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = app.config.get("ADMIN_USERNAME")
            password_hash = app.config.get("ADMIN_PASSWORD_HASH")
            if not username or not password_hash:
                return render_template(
                    "login.html",
                    error="Admin credentials are not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD_HASH.",
                ), 503

            submitted_username = request.form.get("username", "")
            submitted_password = request.form.get("password", "")
            try:
                valid_password = check_password_hash(password_hash, submitted_password)
            except ValueError:
                app.logger.exception("ADMIN_PASSWORD_HASH is not a valid Werkzeug password hash")
                return render_template(
                    "login.html", error="Admin authentication is not configured correctly."
                ), 503

            if submitted_username == username and valid_password:
                session.clear()
                session["admin_logged_in"] = True
                session["admin_username"] = username
                return redirect(url_for("dashboard"))
            return render_template("login.html", error="Invalid username or password."), 401

        return render_template("login.html")

    @app.post("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("admin_login"))

    @app.get("/dashboard")
    @admin_required
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/admin")
    @admin_required
    def admin():
        return render_template("admin.html", stages=ORDER_STAGES)

    # ---------------- feedback CRUD ----------------
    @app.post("/api/feedback")
    def create_feedback():
        d = request.get_json(silent=True) or {}
        errors = validate_feedback(d)
        if errors:
            return jsonify({"errors": errors}), 422
        s = analyze(d["message"])
        fb = Feedback(name=d["name"].strip(), email=d["email"].strip(),
                      category=d.get("category", "General"), rating=int(d["rating"]),
                      message=d["message"].strip(), sentiment=s["label"],
                      sentiment_score=s["score"],
                      product_id=d.get("product_id") or None,
                      order_id=d.get("order_id") or None)
        db.session.add(fb)
        db.session.commit()
        return jsonify(fb.to_dict()), 201

    @app.get("/api/feedback")
    @admin_required
    def list_feedback():
        q = Feedback.query
        if s := request.args.get("sentiment"):
            q = q.filter_by(sentiment=s)
        if c := request.args.get("category"):
            q = q.filter_by(category=c)
        if term := request.args.get("q"):
            q = q.filter(Feedback.message.ilike(f"%{term}%"))
        page = max(int(request.args.get("page", 1)), 1)
        per = min(int(request.args.get("per_page", 20)), 100)
        p = q.order_by(Feedback.created_at.desc()).paginate(page=page, per_page=per, error_out=False)
        return jsonify({"items": [f.to_dict() for f in p.items], "total": p.total,
                        "page": page, "pages": p.pages})

    @app.get("/api/feedback/<int:fid>")
    @admin_required
    def get_feedback(fid):
        fb = db.session.get(Feedback, fid)
        return jsonify(fb.to_dict()) if fb else err("Not found", 404)

    @app.put("/api/feedback/<int:fid>")
    @admin_required
    def update_feedback(fid):
        fb = db.session.get(Feedback, fid)
        if not fb:
            return err("Not found", 404)
        d = request.get_json(silent=True) or {}
        errors = validate_feedback(d, partial=True)
        if errors:
            return jsonify({"errors": errors}), 422
        for k in ("name", "email", "category", "rating"):
            if k in d:
                setattr(fb, k, int(d[k]) if k == "rating" else d[k])
        if "message" in d:
            fb.message = d["message"].strip()
            s = analyze(fb.message)  # re-run sentiment on edit
            fb.sentiment, fb.sentiment_score = s["label"], s["score"]
        db.session.commit()
        return jsonify(fb.to_dict())

    @app.delete("/api/feedback/<int:fid>")
    @admin_required
    def delete_feedback(fid):
        fb = db.session.get(Feedback, fid)
        if not fb:
            return err("Not found", 404)
        db.session.delete(fb)
        db.session.commit()
        return "", 204

    @app.post("/api/analyze")
    def analyze_only():
        d = request.get_json(silent=True) or {}
        return jsonify(analyze(d.get("text", "")))

    # ---------------- analytics ----------------
    @app.get("/api/stats")
    @admin_required
    def stats():
        total = Feedback.query.count()
        by_sent = dict(db.session.query(Feedback.sentiment, func.count()).group_by(Feedback.sentiment).all())
        by_cat = dict(db.session.query(Feedback.category, func.count()).group_by(Feedback.category).all())
        by_rating = dict(db.session.query(Feedback.rating, func.count()).group_by(Feedback.rating).all())
        avg_rating = db.session.query(func.avg(Feedback.rating)).scalar() or 0
        avg_score = db.session.query(func.avg(Feedback.sentiment_score)).scalar() or 0
        # daily trend
        trend = Counter()
        sent_trend = {}
        for f in Feedback.query.with_entities(Feedback.created_at, Feedback.sentiment).all():
            day = f.created_at.strftime("%Y-%m-%d")
            trend[day] += 1
            sent_trend.setdefault(day, {"positive": 0, "neutral": 0, "negative": 0})[f.sentiment] += 1
        days = sorted(trend)
        return jsonify({
            "total": total,
            "avg_rating": round(float(avg_rating), 2),
            "avg_sentiment": round(float(avg_score), 3),
            "by_sentiment": {k: by_sent.get(k, 0) for k in ("positive", "neutral", "negative")},
            "by_category": by_cat,
            "by_rating": {str(i): by_rating.get(i, 0) for i in range(1, 6)},
            "trend": {"labels": days, "counts": [trend[d] for d in days],
                      "sentiment": [sent_trend[d] for d in days]},
        })

    # ---------------- products CRUD ----------------
    @app.get("/api/products")
    def list_products():
        return jsonify([p.to_dict() for p in Product.query.order_by(Product.id).all()])

    @app.post("/api/products")
    @admin_required
    def create_product():
        d = request.get_json(silent=True) or {}
        try:
            name = d["name"].strip(); price = float(d["price"]); stock = int(d.get("stock", 0))
            assert name and price >= 0 and stock >= 0
        except Exception:
            return err("name, price>=0, stock>=0 required", 422)
        if Product.query.filter_by(name=name).first():
            return err("Product name already exists", 409)
        p = Product(name=name, price=price, stock=stock)
        db.session.add(p); db.session.commit()
        return jsonify(p.to_dict()), 201

    @app.put("/api/products/<int:pid>")
    @admin_required
    def update_product(pid):
        p = db.session.get(Product, pid)
        if not p:
            return err("Not found", 404)
        d = request.get_json(silent=True) or {}
        try:
            if "name" in d: p.name = d["name"].strip()
            if "price" in d: p.price = float(d["price"]); assert p.price >= 0
            if "stock" in d: p.stock = int(d["stock"]); assert p.stock >= 0
        except Exception:
            db.session.rollback()
            return err("Invalid values", 422)
        db.session.commit()
        return jsonify(p.to_dict())

    @app.delete("/api/products/<int:pid>")
    @admin_required
    def delete_product(pid):
        p = db.session.get(Product, pid)
        if not p:
            return err("Not found", 404)
        if Order.query.filter_by(product_id=pid).first():
            return err("Product has orders; cannot delete", 409)
        db.session.delete(p); db.session.commit()
        return "", 204

    # ---------------- orders (stock integrity + fulfilment flow) ----------------
    @app.get("/api/orders")
    @admin_required
    def list_orders():
        return jsonify([o.to_dict() for o in Order.query.order_by(Order.id.desc()).all()])

    @app.post("/api/orders")
    @admin_required
    def create_order():
        d = request.get_json(silent=True) or {}
        try:
            qty = int(d["quantity"]); pid = int(d["product_id"]); cust = d["customer_name"].strip()
            assert qty > 0 and cust
        except Exception:
            return err("customer_name, product_id, quantity>0 required", 422)
        # row lock on PostgreSQL/MySQL prevents overselling under concurrency
        p = db.session.query(Product).filter_by(id=pid).with_for_update().first()
        if not p:
            return err("Product not found", 404)
        if p.stock < qty:
            return err(f"Insufficient stock (available: {p.stock})", 409)
        p.stock -= qty
        o = Order(customer_name=cust, product_id=pid, quantity=qty, status="Placed")
        db.session.add(o); db.session.commit()
        return jsonify(o.to_dict()), 201

    @app.patch("/api/orders/<int:oid>/advance")
    @admin_required
    def advance_order(oid):
        o = db.session.get(Order, oid)
        if not o:
            return err("Not found", 404)
        i = ORDER_STAGES.index(o.status)
        if i == len(ORDER_STAGES) - 1:
            return err("Order already delivered", 409)
        o.status = ORDER_STAGES[i + 1]
        db.session.commit()
        return jsonify(o.to_dict())

    @app.delete("/api/orders/<int:oid>")
    @admin_required
    def cancel_order(oid):
        o = db.session.get(Order, oid)
        if not o:
            return err("Not found", 404)
        if o.status != "Placed":
            return err("Only 'Placed' orders can be cancelled", 409)
        o.product.stock += o.quantity  # restock
        db.session.delete(o); db.session.commit()
        return "", 204

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return err("Not found", 404)
        return e


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
