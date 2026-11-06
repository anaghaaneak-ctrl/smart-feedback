import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from app import create_app
from models import db
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD_HASH": generate_password_hash("test-password"),
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.drop_all(); db.create_all()
        from app import seed_if_empty; seed_if_empty()
    return app.test_client()


def login(client):
    return client.post("/admin/login", data={
        "username": "admin", "password": "test-password",
    })


def fb(**kw):
    d = {"name": "Asha", "email": "a@x.com", "rating": 5, "message": "I love this product, amazing!"}
    d.update(kw); return d


def test_positive_sentiment(client):
    r = client.post("/api/feedback", json=fb())
    assert r.status_code == 201 and r.json["sentiment"] == "positive"


def test_negative_sentiment(client):
    r = client.post("/api/feedback", json=fb(rating=1, message="Terrible, broken and awful service"))
    assert r.json["sentiment"] == "negative"


def test_rating_validation(client):
    assert client.post("/api/feedback", json=fb(rating=6)).status_code == 422


def test_crud_cycle(client):
    login(client)
    fid = client.post("/api/feedback", json=fb()).json["id"]
    r = client.put(f"/api/feedback/{fid}", json={"message": "Actually it is horrible and bad"})
    assert r.json["sentiment"] == "negative"
    assert client.delete(f"/api/feedback/{fid}").status_code == 204
    assert client.get(f"/api/feedback/{fid}").status_code == 404


def test_stats(client):
    login(client)
    client.post("/api/feedback", json=fb())
    s = client.get("/api/stats").json
    assert s["total"] == 1 and s["by_sentiment"]["positive"] == 1


def test_order_reduces_stock_and_blocks_oversell(client):
    login(client)
    r = client.post("/api/orders", json={"customer_name": "R", "product_id": 2, "quantity": 4})
    assert r.status_code == 201
    stock = [p for p in client.get("/api/products").json if p["id"] == 2][0]["stock"]
    assert stock == 6
    assert client.post("/api/orders", json={"customer_name": "R", "product_id": 2, "quantity": 7}).status_code == 409


def test_order_stages(client):
    login(client)
    oid = client.post("/api/orders", json={"customer_name": "R", "product_id": 1, "quantity": 1}).json["id"]
    assert client.patch(f"/api/orders/{oid}/advance").json["status"] == "Shipped"
    assert client.patch(f"/api/orders/{oid}/advance").json["status"] == "Delivered"
    assert client.patch(f"/api/orders/{oid}/advance").status_code == 409


def test_admin_pages_redirect_anonymous_users(client):
    assert client.get("/dashboard").status_code == 302
    assert client.get("/admin").status_code == 302
    assert client.get("/admin/login").status_code == 200


def test_admin_apis_reject_anonymous_users(client):
    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/feedback").status_code == 401
    assert client.get("/api/feedback/1").status_code == 401
    assert client.put("/api/feedback/1", json={"message": "Updated feedback"}).status_code == 401
    assert client.delete("/api/feedback/1").status_code == 401
    assert client.post("/api/products", json={"name": "New", "price": 1, "stock": 1}).status_code == 401
    assert client.put("/api/products/1", json={"stock": 1}).status_code == 401
    assert client.delete("/api/products/1").status_code == 401
    assert client.get("/api/orders").status_code == 401
    assert client.post("/api/orders", json={"customer_name": "R", "product_id": 1, "quantity": 1}).status_code == 401
    assert client.patch("/api/orders/1/advance").status_code == 401
    assert client.delete("/api/orders/1").status_code == 401


def test_public_feedback_features_remain_available(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/products").status_code == 200
    assert client.post("/api/analyze", json={"text": "Great service"}).status_code == 200
    assert client.post("/api/feedback", json=fb()).status_code == 201


def test_login_logout_and_session_protection(client):
    assert client.post("/admin/login", data={
        "username": "admin", "password": "wrong",
    }).status_code == 401
    assert login(client).status_code == 302
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert b"Store admin" in dashboard.data and b"Logout" in dashboard.data
    assert client.post("/admin/logout").status_code == 302
    assert client.get("/dashboard").status_code == 302
    assert client.get("/api/stats").status_code == 401


def test_navigation_is_role_aware(client):
    page = client.get("/")
    assert b"Admin login" in page.data
    assert b"Dashboard" not in page.data
    login(client)
    page = client.get("/")
    assert b"Dashboard" in page.data and b"Store admin" in page.data
    assert b"Admin login" not in page.data


def test_login_requires_configured_admin_credentials():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "ADMIN_USERNAME": None,
        "ADMIN_PASSWORD_HASH": None,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
    response = app.test_client().post("/admin/login", data={
        "username": "admin", "password": "test-password",
    })
    assert response.status_code == 503
