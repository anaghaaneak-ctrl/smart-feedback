-- Reference PostgreSQL schema (SQLAlchemy creates these automatically)
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  price NUMERIC(10,2) NOT NULL,
  stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  customer_name VARCHAR(120) NOT NULL,
  product_id INTEGER NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  status VARCHAR(20) NOT NULL DEFAULT 'Placed'
    CHECK (status IN ('Placed','Shipped','Delivered')),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE feedback (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL,
  category VARCHAR(50) NOT NULL DEFAULT 'General',
  rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
  message TEXT NOT NULL,
  sentiment VARCHAR(10) NOT NULL,
  sentiment_score REAL NOT NULL,
  product_id INTEGER REFERENCES products(id),
  order_id INTEGER REFERENCES orders(id),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_feedback_created ON feedback(created_at);
