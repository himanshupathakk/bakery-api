import pytest
import json
from app import create_app
from db import db as _db


# ── FIXTURES ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
#Create application with in-memory test database.
def app():
    app = create_app(db_url="sqlite:///:memory:")
    app.config["TESTING"] = True
    yield app

#Test client.
@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


#Create Base Data for testing
@pytest.fixture(scope="session")
def setup_data(client):
    data = {}

    # Register admin
    r = client.post("/register", json={"username": "admin", "password": "admin123", "role": "admin", "email": "admin@test.com"})
    assert r.status_code == 201

    # Register customer
    r = client.post("/register", json={"username": "alice", "password": "alice123", "role": "customer", "email": "alice@test.com"})
    assert r.status_code == 201
    data["customer_id"] = r.get_json()["id"]

    # Login admin
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    data["admin_token"] = r.get_json()["access_token"]

    # Login customer
    r = client.post("/login", json={"username": "alice", "password": "alice123"})
    data["customer_token"] = r.get_json()["access_token"]

    # Create category
    r = client.post("/categories",
                    json={"name": "Cakes", "description": "All cakes"},
                    headers={"Authorization": f"Bearer {data['admin_token']}"})
    data["category_id"] = r.get_json()["id"]

    # Create product
    r = client.post("/products",
                    json={"name": "Chocolate Cake", "price": 24.99, "stock_quantity": 10, "category_id": data["category_id"]},
                    headers={"Authorization": f"Bearer {data['admin_token']}"})
    data["product_id"] = r.get_json()["id"]

    # Create tag
    r = client.post("/tags",
                    json={"name": "bestseller"},
                    headers={"Authorization": f"Bearer {data['admin_token']}"})
    data["tag_id"] = r.get_json()["id"]

    return data


#Helper — returns auth header dict.
def ah(token):
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# 🔐 AUTH TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestAuth:

    #New user registers successfully.
    def test_register_success(self, client):
        r = client.post("/register", json={"username": "bob", "password": "bob123", "role": "customer"})
        assert r.status_code == 201
        d = r.get_json()
        assert d["username"] == "bob"
        assert d["role"] == "customer"
        assert "password" not in d  # password never returned

    #Admin role is saved correctly.
    def test_register_admin_role(self, client):
        r = client.post("/register", json={"username": "admin2", "password": "pass123", "role": "admin"})
        assert r.status_code == 201
        assert r.get_json()["role"] == "admin"

    #Duplicate username returns 409.
    def test_register_duplicate_username(self, client, setup_data):
        r = client.post("/register", json={"username": "admin", "password": "anything"})
        assert r.status_code == 409

    #Login returns access token.
    def test_login_success(self, client):
        r = client.post("/login", json={"username": "alice", "password": "alice123"})
        assert r.status_code == 200
        d = r.get_json()
        assert "access_token" in d
        assert d["user"]["username"] == "alice"
        assert d["user"]["role"] == "customer"

    #Wrong password returns 401.
    def test_login_wrong_password(self, client):
        r = client.post("/login", json={"username": "alice", "password": "wrongpass"})
        assert r.status_code == 401

    #Non-existent user returns 401.
    def test_login_nonexistent_user(self, client):
        r = client.post("/login", json={"username": "nobody", "password": "pass123"})
        assert r.status_code == 401

    #Logout clears token.
    def test_logout(self, client, setup_data):
        r = client.post("/logout", headers=ah(setup_data["admin_token"]))
        # Re-login admin so token is still valid for other tests
        r2 = client.post("/login", json={"username": "admin", "password": "admin123"})
        setup_data["admin_token"] = r2.get_json()["access_token"]
        assert r.status_code == 200

    #Protected route without token returns 401.
    def test_protected_route_no_token(self, client):
        r = client.post("/categories", json={"name": "Test"})
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 📂 CATEGORY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCategories:

    def test_get_all_categories_public(self, client):
        """Anyone can list categories without token."""
        r = client.get("/categories")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_get_category_by_id_public(self, client, setup_data):
        """Anyone can get category by ID."""
        r = client.get(f"/categories/{setup_data['category_id']}")
        assert r.status_code == 200
        assert r.get_json()["name"] == "Cakes"

    def test_admin_creates_category(self, client, setup_data):
        """Admin can create a category."""
        r = client.post("/categories",
                        json={"name": "Pastries", "description": "Croissants etc"},
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 201
        assert r.get_json()["name"] == "Pastries"

    def test_customer_cannot_create_category(self, client, setup_data):
        """Customer is blocked from creating categories (403)."""
        r = client.post("/categories",
                        json={"name": "Hack"},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_duplicate_category_name(self, client, setup_data):
        """Duplicate category name returns 400."""
        r = client.post("/categories",
                        json={"name": "Cakes"},
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 400

    def test_admin_updates_category(self, client, setup_data):
        """Admin can update a category."""
        r = client.put(f"/categories/{setup_data['category_id']}",
                       json={"name": "Cakes", "description": "Updated description"},
                       headers=ah(setup_data["admin_token"]))
        assert r.status_code == 200
        assert r.get_json()["description"] == "Updated description"

    def test_customer_cannot_update_category(self, client, setup_data):
        """Customer cannot update category (403)."""
        r = client.put(f"/categories/{setup_data['category_id']}",
                       json={"name": "Hacked"},
                       headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_get_nonexistent_category(self, client):
        """Non-existent category returns 404."""
        r = client.get("/categories/9999")
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 🎂 PRODUCT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestProducts:

    def test_get_all_products_public(self, client):
        """Anyone can list products."""
        r = client.get("/products")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_get_product_by_id_public(self, client, setup_data):
        """Anyone can get product by ID."""
        r = client.get(f"/products/{setup_data['product_id']}")
        assert r.status_code == 200
        d = r.get_json()
        assert d["name"] == "Chocolate Cake"
        assert d["price"] == 24.99
        assert d["stock_quantity"] == 10

    def test_product_has_category(self, client, setup_data):
        """Product response includes nested category."""
        r = client.get(f"/products/{setup_data['product_id']}")
        d = r.get_json()
        assert d["category"] is not None
        assert d["category"]["name"] == "Cakes"

    def test_admin_creates_product(self, client, setup_data):
        """Admin can create a product."""
        r = client.post("/products",
                        json={"name": "Red Velvet", "price": 29.99, "stock_quantity": 5,
                              "category_id": setup_data["category_id"]},
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 201
        assert r.get_json()["name"] == "Red Velvet"

    def test_customer_cannot_create_product(self, client, setup_data):
        """Customer blocked from creating products (403)."""
        r = client.post("/products",
                        json={"name": "Hack", "price": 1, "stock_quantity": 1},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_no_token_cannot_create_product(self, client):
        """No token returns 401."""
        r = client.post("/products", json={"name": "Test", "price": 1, "stock_quantity": 1})
        assert r.status_code == 401

    def test_admin_updates_product(self, client, setup_data):
        """Admin can update product price and stock."""
        r = client.put(f"/products/{setup_data['product_id']}",
                       json={"price": 27.99, "stock_quantity": 15},
                       headers=ah(setup_data["admin_token"]))
        assert r.status_code == 200
        d = r.get_json()
        assert d["price"] == 27.99
        assert d["stock_quantity"] == 15

    def test_customer_cannot_update_product(self, client, setup_data):
        """Customer cannot update products (403)."""
        r = client.put(f"/products/{setup_data['product_id']}",
                       json={"price": 1.0},
                       headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_get_products_by_category(self, client, setup_data):
        """Can filter products by category."""
        r = client.get(f"/categories/{setup_data['category_id']}/products")
        assert r.status_code == 200
        products = r.get_json()
        assert len(products) >= 1

    def test_get_nonexistent_product(self, client):
        """Non-existent product returns 404."""
        r = client.get("/products/9999")
        assert r.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 🏷️ TAG TESTS (Many-to-Many)
# ══════════════════════════════════════════════════════════════════════════════

class TestTags:

    def test_get_all_tags_public(self, client):
        """Anyone can list tags."""
        r = client.get("/tags")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_admin_creates_tag(self, client, setup_data):
        """Admin can create a tag."""
        r = client.post("/tags",
                        json={"name": "new"},
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 201
        assert r.get_json()["name"] == "new"

    def test_customer_cannot_create_tag(self, client, setup_data):
        """Customer blocked from creating tags (403)."""
        r = client.post("/tags",
                        json={"name": "hack"},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_duplicate_tag_name(self, client, setup_data):
        """Duplicate tag name returns 400."""
        r = client.post("/tags",
                        json={"name": "bestseller"},
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 400

    def test_link_tag_to_product(self, client, setup_data):
        """Admin can link tag to product (many-to-many)."""
        r = client.post(f"/products/{setup_data['product_id']}/tags/{setup_data['tag_id']}",
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 201
        d = r.get_json()
        assert any(t["name"] == "bestseller" for t in d["tags"])

    def test_link_duplicate_tag(self, client, setup_data):
        """Linking same tag twice returns 400."""
        r = client.post(f"/products/{setup_data['product_id']}/tags/{setup_data['tag_id']}",
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 400

    def test_get_product_tags(self, client, setup_data):
        """Can get all tags for a product."""
        r = client.get(f"/products/{setup_data['product_id']}/tags")
        assert r.status_code == 200
        tags = r.get_json()["tags"]
        assert any(t["name"] == "bestseller" for t in tags)

    def test_customer_cannot_link_tag(self, client, setup_data):
        """Customer cannot link tags (403)."""
        r = client.post(f"/products/{setup_data['product_id']}/tags/{setup_data['tag_id']}",
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_unlink_tag_from_product(self, client, setup_data):
        """Admin can unlink tag from product."""
        r = client.delete(f"/products/{setup_data['product_id']}/tags/{setup_data['tag_id']}",
                          headers=ah(setup_data["admin_token"]))
        assert r.status_code == 200
        d = r.get_json()
        assert not any(t["name"] == "bestseller" for t in d["tags"])


# ══════════════════════════════════════════════════════════════════════════════
# 🛒 ORDER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestOrders:

    def test_place_order_success(self, client, setup_data):
        """Customer can place an order and stock is deducted."""
        # First check current stock
        r = client.get(f"/products/{setup_data['product_id']}")
        stock_before = r.get_json()["stock_quantity"]

        r = client.post("/orders",
                        json={"items": [{"product_id": setup_data["product_id"], "quantity": 2}],
                              "note": "Extra packaging"},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 201
        d = r.get_json()
        assert d["status"] == "pending"
        assert d["total_price"] > 0
        setup_data["order_id"] = d["id"]

        # Check stock was deducted
        r2 = client.get(f"/products/{setup_data['product_id']}")
        stock_after = r2.get_json()["stock_quantity"]
        assert stock_after == stock_before - 2

    def test_order_has_items(self, client, setup_data):
        """Order response includes nested order items."""
        r = client.get(f"/orders/{setup_data['order_id']}",
                       headers=ah(setup_data["customer_token"]))
        assert r.status_code == 200
        d = r.get_json()
        assert len(d["order_items"]) == 1
        assert d["order_items"][0]["product"]["name"] == "Chocolate Cake"
        assert d["order_items"][0]["quantity"] == 2

    def test_customer_sees_own_orders(self, client, setup_data):
        """Customer can only see their own orders."""
        r = client.get("/orders", headers=ah(setup_data["customer_token"]))
        assert r.status_code == 200
        orders = r.get_json()
        assert all(o["user"]["username"] == "alice" for o in orders)

    def test_admin_sees_all_orders(self, client, setup_data):
        """Admin sees all orders."""
        r = client.get("/orders", headers=ah(setup_data["admin_token"]))
        assert r.status_code == 200
        assert len(r.get_json()) >= 1

    def test_order_requires_jwt(self, client):
        """Orders require authentication."""
        r = client.get("/orders")
        assert r.status_code == 401

    def test_insufficient_stock(self, client, setup_data):
        """Order with more quantity than stock returns 400."""
        r = client.post("/orders",
                        json={"items": [{"product_id": setup_data["product_id"], "quantity": 9999}]},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 400

    def test_admin_updates_order_status(self, client, setup_data):
        """Admin can update order status."""
        r = client.patch(f"/orders/{setup_data['order_id']}/status",
                         json={"status": "confirmed"},
                         headers=ah(setup_data["admin_token"]))
        assert r.status_code == 200
        assert r.get_json()["status"] == "confirmed"

    def test_customer_cannot_update_status(self, client, setup_data):
        """Customer cannot update order status (403)."""
        r = client.patch(f"/orders/{setup_data['order_id']}/status",
                         json={"status": "delivered"},
                         headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_cannot_cancel_confirmed_order(self, client, setup_data):
        """Cannot cancel a confirmed order."""
        r = client.delete(f"/orders/{setup_data['order_id']}",
                          headers=ah(setup_data["customer_token"]))
        assert r.status_code == 400

    def test_cancel_pending_order_restores_stock(self, client, setup_data):
        """Cancelling a pending order restores stock."""
        # Place a new pending order
        r = client.get(f"/products/{setup_data['product_id']}")
        stock_before = r.get_json()["stock_quantity"]

        r = client.post("/orders",
                        json={"items": [{"product_id": setup_data["product_id"], "quantity": 1}]},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 201
        new_order_id = r.get_json()["id"]

        # Cancel it
        r = client.delete(f"/orders/{new_order_id}",
                          headers=ah(setup_data["customer_token"]))
        assert r.status_code == 200

        # Stock should be restored
        r = client.get(f"/products/{setup_data['product_id']}")
        stock_after = r.get_json()["stock_quantity"]
        assert stock_after == stock_before

    def test_invalid_status_value(self, client, setup_data):
        """Invalid status value returns 422."""
        r = client.patch(f"/orders/{setup_data['order_id']}/status",
                         json={"status": "flying"},
                         headers=ah(setup_data["admin_token"]))
        assert r.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# ⭐ REVIEW TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestReviews:

    def test_get_reviews_public(self, client, setup_data):
        """Anyone can get product reviews."""
        r = client.get(f"/products/{setup_data['product_id']}/reviews")
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_add_review(self, client, setup_data):
        """Customer can add a review."""
        r = client.post(f"/products/{setup_data['product_id']}/reviews",
                        json={"rating": 5, "comment": "Absolutely delicious!"},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 201
        d = r.get_json()
        assert d["rating"] == 5
        assert d["comment"] == "Absolutely delicious!"
        assert d["user"]["username"] == "alice"
        setup_data["review_id"] = d["id"]

    def test_duplicate_review_blocked(self, client, setup_data):
        """Cannot review the same product twice."""
        r = client.post(f"/products/{setup_data['product_id']}/reviews",
                        json={"rating": 3, "comment": "Second review"},
                        headers=ah(setup_data["customer_token"]))
        assert r.status_code == 400

    def test_rating_must_be_1_to_5(self, client, setup_data):
        """Rating outside 1-5 returns 422."""
        r = client.post(f"/products/{setup_data['product_id']}/reviews",
                        json={"rating": 10},
                        headers=ah(setup_data["admin_token"]))
        assert r.status_code == 422

    def test_review_requires_jwt(self, client, setup_data):
        """Adding review without token returns 401."""
        r = client.post(f"/products/{setup_data['product_id']}/reviews",
                        json={"rating": 4})
        assert r.status_code == 401

    def test_review_appears_on_product(self, client, setup_data):
        """Review appears in product response."""
        r = client.get(f"/products/{setup_data['product_id']}")
        d = r.get_json()
        assert len(d["reviews"]) >= 1
        assert d["reviews"][0]["rating"] == 5

    def test_delete_own_review(self, client, setup_data):
        """User can delete their own review."""
        r = client.delete(f"/reviews/{setup_data['review_id']}",
                          headers=ah(setup_data["customer_token"]))
        assert r.status_code == 200

    def test_delete_other_review_blocked(self, client, setup_data):
        """Cannot delete someone else's review (403)."""
        # Add review as admin first
        r = client.post(f"/products/{setup_data['product_id']}/reviews",
                        json={"rating": 4, "comment": "Admin review"},
                        headers=ah(setup_data["admin_token"]))
        admin_review_id = r.get_json()["id"]

        # Customer tries to delete admin's review
        r = client.delete(f"/reviews/{admin_review_id}",
                          headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# 👤 USER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestUsers:

    def test_get_all_users_requires_jwt(self, client):
        """Getting users requires authentication."""
        r = client.get("/users")
        assert r.status_code == 401

    def test_get_all_users(self, client, setup_data):
        """Authenticated user can get all users."""
        r = client.get("/users", headers=ah(setup_data["admin_token"]))
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)
        assert len(r.get_json()) >= 2

    def test_get_user_by_id(self, client, setup_data):
        """Can get user by ID."""
        r = client.get(f"/users/{setup_data['customer_id']}",
                       headers=ah(setup_data["customer_token"]))
        assert r.status_code == 200
        assert r.get_json()["username"] == "alice"

    def test_update_own_email(self, client, setup_data):
        """User can update their own email."""
        r = client.put(f"/users/{setup_data['customer_id']}",
                       json={"email": "newalice@example.com"},
                       headers=ah(setup_data["customer_token"]))
        assert r.status_code == 200
        assert r.get_json()["email"] == "newalice@example.com"

    def test_cannot_update_other_user(self, client, setup_data):
        """Cannot update another user's profile (403)."""
        r = client.put("/users/1",
                       json={"email": "hack@hack.com"},
                       headers=ah(setup_data["customer_token"]))
        assert r.status_code == 403

    def test_change_password_wrong_current(self, client, setup_data):
        """Wrong current password returns 401."""
        r = client.patch(f"/users/{setup_data['customer_id']}/password",
                         json={"current_password": "wrongpass", "new_password": "newpass123"},
                         headers=ah(setup_data["customer_token"]))
        assert r.status_code == 401

    def test_change_password_too_short(self, client, setup_data):
        """New password too short returns 400."""
        r = client.patch(f"/users/{setup_data['customer_id']}/password",
                         json={"current_password": "alice123", "new_password": "ab"},
                         headers=ah(setup_data["customer_token"]))
        assert r.status_code == 400

    def test_change_password_success(self, client, setup_data):
        """Correct current password allows change."""
        r = client.patch(f"/users/{setup_data['customer_id']}/password",
                         json={"current_password": "alice123", "new_password": "newpass123"},
                         headers=ah(setup_data["customer_token"]))
        assert r.status_code == 200
        # Login with new password works
        r2 = client.post("/login", json={"username": "alice", "password": "newpass123"})
        assert r2.status_code == 200
        setup_data["customer_token"] = r2.get_json()["access_token"]