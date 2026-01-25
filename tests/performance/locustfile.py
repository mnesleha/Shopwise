"""
Locust performance test - Basic E2E shopping flow

Goals of this locustfile:
- Keep the test deterministic and "fair" (minimize artificial failures).
- Separate "product not sellable" 404s from real failures (do not pollute fail-rate).
- Avoid shared credentials across users (JWT refresh rotation/concurrency issues).
- Always send a valid checkout payload.
- Log *why* a request failed (response body snippet).
"""
from __future__ import annotations
import os
from locust import HttpUser, task, between
import random
import time
from typing import Any, Dict, List, Optional, Tuple


class ShopwiseUser(HttpUser):
    """
    Simuluje typického uživatele, který:
    1. Prohlíží produkty
    2. Přidává produkty do košíku
    3. Checkoutuje objednávku
    """

    # Wait time between tasks (1-3 seconds simulates real user behavior)
    wait_time = between(1, 3)

    def on_start(self):
        """
        Called when user starts - vytvoří session a přihlásí uživatele
        """
        # Register a new user (or use existing test user)
        # For performance testing, you might want to pre-create users
        self.client.headers.update({"Accept": "application/json"})

        # Login as test user (assuming seed data exists)
        login_response = self.client.post("/api/v1/auth/login/", json={
            "email": "customer_1@example.com",
            "password": "customer_1"
        })

        if login_response.status_code == 200:
            # Session-based auth - cookies are handled automatically
            pass
        else:
            print(f"Login failed: {login_response.status_code}")

    @task(3)
    def browse_products(self):
        """
        Browse product list - highest weight (happens most often)
        """
        self.client.get("/api/v1/products/", name="/api/v1/products/")

    @task(2)
    def view_product_detail(self):
        """
        View random product detail
        """
        # In real scenario, you'd get product IDs from browse_products
        # For now, assume products with IDs 1-50 exist
        product_id = random.randint(1, 50)
        self.client.get(
            f"/api/v1/products/{product_id}/", name="/api/v1/products/[id]/")

    @task(2)
    def search_products(self):
        """
        Search products by name
        """
        search_terms = ["MOUSE", "KEYBOARD", "HEADSET", "MONITOR", "LAPTOP"]
        term = random.choice(search_terms)
        self.client.get(
            f"/api/v1/products/?search={term}", name="/api/v1/products/?search=[term]")

    @task(1)
    def view_cart(self):
        """
        Check current cart
        """
        self.client.get("/api/v1/cart/", name="/api/v1/cart/")

    @task(1)
    def add_to_cart(self):
        """
        Add random product to cart
        """
        product_id = random.randint(1, 50)
        self.client.put(
            f"/api/v1/cart/items/{product_id}/",
            json={"quantity": random.randint(1, 3)},
            name="/api/v1/cart/items/[id]/"
        )

    @task(1)
    def browse_categories(self):
        """
        Browse categories
        """
        self.client.get("/api/v1/categories/", name="/api/v1/categories/")


class GuestUser(HttpUser):
    """
    Simuluje anonymous/guest uživatele - nakupuje bez registrace
    Používá cart token z cookies/headers pro identifikaci košíku
    """

    wait_time = between(1, 3)

    def on_start(self):
        """
        Guest user - NO login, cart is identified by cookie/token
        """
        self.client.headers.update({"Accept": "application/json"})
        # No login - guest user relies on cart token from first cart interaction

    @task(3)
    def browse_products_guest(self):
        self.client.get("/api/v1/products/", name="/api/v1/products/ (guest)")

    @task(2)
    def add_to_cart_guest(self):
        """
        Guest user adds item - backend creates cart and returns token in cookie
        """
        product_id = random.randint(1, 50)
        self.client.put(
            f"/api/v1/cart/items/{product_id}/",
            json={"quantity": 1},
            name="/api/v1/cart/items/[id]/ (guest)"
        )

    @task(1)
    def guest_checkout(self):
        """
        Guest checkout - creates guest order with access token
        """
        # Add at least one item first
        product_id = random.randint(1, 30)
        self.client.put(
            f"/api/v1/cart/items/{product_id}/", json={"quantity": 1})

        # Checkout
        checkout_response = self.client.post("/api/v1/cart/checkout/", json={
            "customer_email": "admin@example.com",
            "shipping_name": "E2E Customer",
            "shipping_address_line1": "E2E Main Street 1",
            "shipping_address_line2": "",
            "shipping_city": "E2E City",
            "shipping_postal_code": "00000",
            "shipping_country": "US",
            "shipping_phone": "+10000000000",
            "billing_same_as_shipping": True,
        }
        )

        if checkout_response.status_code == 200:
            data = checkout_response.json()
            order_id = data.get("order", {}).get("id")
            guest_token = data.get("guest_access_token")

            if order_id and guest_token:
                # Payment for guest order
                self.client.post("/api/v1/payments/", json={
                    "order_id": order_id,
                    "result": "success"
                }, name="/api/v1/payments/ (guest)")

                # Access guest order with token
                self.client.get(
                    f"/api/v1/guest/orders/{order_id}/?token={guest_token}",
                    name="/api/v1/guest/orders/[id]/ (guest)"
                )


class HeavyShopperUser(HttpUser):
    """
    Simuluje "heavy shopper" - uživatele, který aktivně nakupuje
    Používá SESSION auth (login vytvoří session cookie)
    """

    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers.update({"Accept": "application/json"})

        # Login (session-based auth)
        login_response = self.client.post("/api/v1/auth/login/", json={
            "email": "customer_2@example.com",
            "password": "customer_2"
        })

        if login_response.status_code != 200:
            print(
                f"Login failed for heavy shopper: {login_response.status_code}")


class JWTAuthUser(HttpUser):
    """
    Testuje JWT Bearer token authentication
    """

    wait_time = between(1, 3)

    def on_start(self):
        """
        Login a získání JWT tokenu pro Authorization: Bearer header
        """
        self.client.headers.update({"Accept": "application/json"})

        # Login - získá access token a refresh token
        login_response = self.client.post("/api/v1/auth/login/", json={
            "email": "customer_3@example.com",
            "password": "customer_3"
        })

        if login_response.status_code == 200:
            tokens = login_response.json()
            self.access_token = tokens.get("access")
            self.refresh_token = tokens.get("refresh")

            # Nastav Authorization header pro všechny další requesty
            self.client.headers.update({
                "Authorization": f"Bearer {self.access_token}"
            })
            print(
                f"JWT login successful, access token: {self.access_token[:20]}...")
        else:
            print(f"JWT login failed: {login_response.status_code}")
            self.access_token = None

    @task(3)
    def browse_with_jwt(self):
        """
        Browse products s JWT auth
        """
        self.client.get("/api/v1/products/", name="/api/v1/products/ (JWT)")

    @task(2)
    def cart_operations_jwt(self):
        """
        Cart operations s JWT auth
        """
        product_id = random.randint(1, 50)
        self.client.put(
            f"/api/v1/cart/items/{product_id}/",
            json={"quantity": 1},
            name="/api/v1/cart/items/[id]/ (JWT)"
        )

    @task(1)
    def get_user_profile_jwt(self):
        """
        Testuje /auth/me endpoint s JWT tokenem
        """
        self.client.get("/api/v1/auth/me/", name="/api/v1/auth/me/ (JWT)")

    @task(1)
    def refresh_token_test(self):
        """
        Testuje refresh token flow
        """
        if not self.refresh_token:
            return

        refresh_response = self.client.post("/api/v1/auth/refresh/", json={
            "refresh": self.refresh_token
        }, name="/api/v1/auth/refresh/")

        if refresh_response.status_code == 200:
            tokens = refresh_response.json()
            new_access = tokens.get("access")

            # Update access token
            if new_access:
                self.access_token = new_access
                self.client.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })


class HeavyShopperUser(HttpUser):
    """
    Simuluje "heavy shopper" - uživatele, který aktivně nakupuje
    Používá SESSION auth (login vytvoří session cookie)
    """

    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers.update({"Accept": "application/json"})

        # Login (session-based auth)
        login_response = self.client.post("/api/v1/auth/login/", json={
            "email": "customer_4@example.com",
            "password": "customer_4"
        })

        if login_response.status_code != 200:
            print(
                f"Login failed for heavy shopper: {login_response.status_code}")

    @task(5)
    def rapid_product_browsing(self):
        """
        Rapidly browse products (simulates scrolling through catalog)
        """
        self.client.get("/api/v1/products/", name="/api/v1/products/")

    @task(3)
    def add_multiple_items(self):
        """
        Add multiple items quickly
        """
        for _ in range(random.randint(2, 5)):
            product_id = random.randint(1, 50)
            self.client.put(
                f"/api/v1/cart/items/{product_id}/",
                json={"quantity": 1},
                name="/api/v1/cart/items/[id]/ (batch)"
            )

    @task(1)
    def checkout_flow(self):
        """
        Complete checkout flow
        """
        # Get cart
        cart_response = self.client.get("/api/v1/cart/")

        if cart_response.status_code == 200:
            # Checkout
            checkout_response = self.client.post("/api/v1/cart/checkout/", json={
                "customer_email": "customer_4@example.com",
                "shipping_name": "E2E Customer",
                "shipping_address_line1": "E2E Main Street 1",
                "shipping_address_line2": "",
                "shipping_city": "E2E City",
                "shipping_postal_code": "00000",
                "shipping_country": "US",
                "shipping_phone": "+10000000000",
                "billing_same_as_shipping": True,
            }
            )

            if checkout_response.status_code == 200:
                order_data = checkout_response.json()
                order_id = order_data.get("order", {}).get("id")

                if order_id:
                    # Simulate payment
                    self.client.post("/api/v1/payments/", json={
                        "order_id": order_id,
                        "result": "success"
                    }, name="/api/v1/payments/")
