# 🎂 Sweet Crumbs Bakery API

A full e-commerce REST API for a bakery shop built with Flask, SQLAlchemy, JWT, and Marshmallow.

## Tech Stack
- Python 3.11 + Flask + Flask-Smorest
- Flask-SQLAlchemy (SQLite)
- Flask-JWT-Extended
- Marshmallow
- Docker

## Run Locally
```bash
pip install -r requirements.txt
python app.py
```

## Run with Docker
```bash
docker compose up --build
```

## URLs
- Shop UI: http://localhost:5000/shop
- Admin UI: http://localhost:5000/admin
- Swagger: http://localhost:5000/swagger-ui

## Relationships
- Category → Products (one-to-many)
- User → Orders (one-to-many)
- User → Reviews (one-to-many)
- Order → OrderItems (one-to-many)
- Product ↔ Tags (many-to-many via products_tags)
- Order ↔ Products (many-to-many via OrderItems)
