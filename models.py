from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

ORDER_STAGES = ["Placed", "Shipped", "Delivered"]


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.CheckConstraint("stock >= 0", name="ck_stock_nonnegative"),)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "price": float(self.price),
                "stock": self.stock, "available": self.stock > 0,
                "created_at": self.created_at.isoformat()}


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Placed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    product = db.relationship("Product")

    def to_dict(self):
        return {"id": self.id, "customer_name": self.customer_name,
                "product_id": self.product_id,
                "product_name": self.product.name if self.product else None,
                "quantity": self.quantity, "status": self.status,
                "created_at": self.created_at.isoformat()}


class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="General")
    rating = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(10), nullable=False)
    sentiment_score = db.Column(db.Float, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    product = db.relationship("Product")
    __table_args__ = (db.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating"),)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email,
                "category": self.category, "rating": self.rating,
                "message": self.message, "sentiment": self.sentiment,
                "sentiment_score": self.sentiment_score,
                "product_id": self.product_id,
                "product_name": self.product.name if self.product else None,
                "order_id": self.order_id,
                "created_at": self.created_at.isoformat()}
