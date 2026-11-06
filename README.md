# Smart Feedback Collection & Analysis System (Python / Flask)

Full-stack app: responsive HTML/CSS/JS frontend → Flask REST API → VADER sentiment analysis →
SQL database (SQLite / PostgreSQL / MySQL) → Chart.js dashboard. Includes a small store admin
(products with stock integrity, orders flowing Placed → Shipped → Delivered).

## Structure
```
app.py              Flask app + REST routes
models.py           SQLAlchemy models (Product, Order, Feedback)
sentiment.py        VADER sentiment service
schema.sql          Reference PostgreSQL schema
templates/          index (submit), login, dashboard (charts), admin (CRUD)
static/css, js      Styles and frontend logic (ES6, fetch API)
tests/test_api.py   pytest suite
postman_collection.json
```

## Run
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # Windows PowerShell; configure required values below
python app.py
```
Set a persistent random `SECRET_KEY`, `ADMIN_USERNAME`, and a Werkzeug password hash
in `.env` before running the app. Generate values from the project environment:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Admin password: ')))"
```
The password prompt does not echo the password. Copy the complete generated hash into
`ADMIN_PASSWORD_HASH` and the generated random value into `SECRET_KEY` in `.env`; do
not commit `.env`. Only the hash is stored, not the administrator password.

Open http://localhost:5000 to submit feedback. Administrators can sign in at
`/admin/login`; successful login opens `/dashboard`. The store management page is
available at `/admin`. The dashboard and management APIs require an admin session.

## Tests
```bash
pytest -q
```

## API
| Method | Endpoint | Description |
|---|---|---|
| POST | /api/feedback | Public: create feedback (auto sentiment) |
| GET | /api/feedback?q=&sentiment=&category=&page= | Admin: list / filter / paginate |
| GET/PUT/DELETE | /api/feedback/{id} | Admin: read / update (re-analyses) / delete |
| POST | /api/analyze | Public: sentiment preview for feedback |
| GET | /api/stats | Admin: aggregates for charts |
| GET | /api/products | Public: product choices for feedback form |
| POST | /api/products | Admin: create product |
| PUT/DELETE | /api/products/{id} | Admin: update stock/price / delete |
| GET/POST | /api/orders | Admin: list / place (decrements stock, blocks oversell) |
| PATCH | /api/orders/{id}/advance | Admin: Placed → Shipped → Delivered |
| DELETE | /api/orders/{id} | Admin: cancel a Placed order (restocks) |

Import `postman_collection.json` into Postman to test every endpoint.

## Git
```bash
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/<you>/smart-feedback.git && git push -u origin main
```
