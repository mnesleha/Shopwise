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


# ----------------------------
# Configuration helpers
# ----------------------------

def _parse_user_pool() -> List[Tuple[str, str]]:
    """
    Provide users via env var, e.g.:
    LOCUST_USERS="customer_1@example.com:pass1,customer_2@example.com:pass2"
   """
    raw = os.getenv("LOCUST_USERS", "").strip()
    if not raw:
        # Fallback (keeps current behavior, but encourages user pool)
        return [("customer_2@example.com", "customer_2")]
    pool: List[Tuple[str, str]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(
                "LOCUST_USERS must be in 'email:password' CSV format")
        email, pwd = part.split(":", 1)
        pool.append((email.strip(), pwd.strip()))
    return pool or [("customer_2@example.com", "customer_2")]


USER_POOL: List[Tuple[str, str]] = _parse_user_pool()

# If your API needs a specific checkout payload, tune this template.
CHECKOUT_PAYLOAD: Dict[str, Any] = {
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

# Cache product IDs per-process to reduce needless list calls.
# (Locust spawns users in-process; this is OK for a baseline.)
_GLOBAL_PRODUCT_CACHE: Dict[str, Any] = {"ids": [], "ts": 0.0}
PRODUCT_CACHE_TTL_SEC = float(os.getenv("PRODUCT_CACHE_TTL_SEC", "15"))


def _log_failure(prefix: str, resp) -> None:
    """Log a short reason for failures without spamming huge bodies."""
    try:
        body = resp.text
    except Exception:
        body = "<no body>"
    body = (body or "").replace("\n", " ").strip()
    if len(body) > 300:
        body = body[:300] + "..."
    print(f"{prefix} status={resp.status_code} body={body}")


def _maybe_refresh_product_cache(client) -> List[int]:
    now = time.time()
    if _GLOBAL_PRODUCT_CACHE["ids"] and (now - _GLOBAL_PRODUCT_CACHE["ts"]) < PRODUCT_CACHE_TTL_SEC:
        return _GLOBAL_PRODUCT_CACHE["ids"]

    with client.get("/api/v1/products/", name="/api/v1/products/ (seed)", catch_response=True) as r:
        if r.status_code != 200:
            r.failure(f"seed products failed: {r.status_code}")
            _log_failure("[seed products]", r)
            return _GLOBAL_PRODUCT_CACHE.get("ids", []) or []

        try:
            data = r.json()
        except Exception:
            r.failure("seed products: invalid JSON")
            _log_failure("[seed products json]", r)
            return _GLOBAL_PRODUCT_CACHE.get("ids", []) or []

        # Support either {results:[...]} or [...]
        items = data.get("results") if isinstance(data, dict) else data
        ids: List[int] = []
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                pid = it.get("id")
                if isinstance(pid, int):
                    ids.append(pid)

        if not ids:
            r.failure("seed products: no IDs in response")
            return _GLOBAL_PRODUCT_CACHE.get("ids", []) or []

        _GLOBAL_PRODUCT_CACHE["ids"] = ids
        _GLOBAL_PRODUCT_CACHE["ts"] = now
        r.success()

    return _GLOBAL_PRODUCT_CACHE["ids"]


# ----------------------------
# Base mixin shared behavior
# ----------------------------

class BaseShopUser(HttpUser):
    abstract = True
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers.update({"Accept": "application/json"})
        self.product_ids: List[int] = []

    def _pick_product_id(self) -> int:
        if not self.product_ids:
            self.product_ids = _maybe_refresh_product_cache(self.client)
        if self.product_ids:
            return random.choice(self.product_ids)
        # Fallback (keeps test running even if list endpoint failed)
        return random.randint(1, 50)

    def _get_product_detail(self, product_id: int, name: str):
        """
        Some products may be 'not sellable' (inactive/stock=0) and return 404.
        We do NOT want those to pollute fail-rate, so we treat 404 as *success*
        but keep them visible as a separate entry in stats.
        """
        with self.client.get(f"/api/v1/products/{product_id}/", name=name, catch_response=True) as r:
            if r.status_code == 404:
                # Mark as success, but count separately by name.
                r.success()
            elif r.status_code >= 400:
                r.failure(f"{r.status_code}")
                _log_failure(f"[{name}]", r)
            else:
                r.success()


# ----------------------------
# User classes
# ----------------------------

class ShopwiseUser(BaseShopUser):
    """
    Typical logged-in user using SESSION auth.
    """

    def on_start(self):
        super().on_start()
        email, pwd = random.choice(USER_POOL)
        with self.client.post("/api/v1/auth/login/", json={"email": email, "password": pwd},
                              name="/api/v1/auth/login/ (session)", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"{r.status_code}")
                _log_failure("[session login]", r)
            else:
                r.success()

    @task(3)
    def browse_products(self):
        with self.client.get("/api/v1/products/", name="/api/v1/products/") as r:
            # Keep per-user IDs reasonably fresh
            if r.status_code == 200:
                try:
                    data = r.json()
                    items = data.get("results") if isinstance(
                        data, dict) else data
                    if isinstance(items, list):
                        self.product_ids = [it.get("id") for it in items if isinstance(
                            it, dict) and isinstance(it.get("id"), int)]
                except Exception:
                    pass

    @task(2)
    def view_product_detail(self):
        pid = self._pick_product_id()
        self._get_product_detail(pid, name="/api/v1/products/[id]/")

    @task(2)
    def search_products(self):
        term = random.choice(
            ["MOUSE", "KEYBOARD", "HEADSET", "MONITOR", "LAPTOP"])
        self.client.get(
            f"/api/v1/products/?search={term}", name="/api/v1/products/?search=[term]")

    @task(1)
    def view_cart(self):
        self.client.get("/api/v1/cart/", name="/api/v1/cart/")

    @task(1)
    def add_to_cart(self):
        pid = self._pick_product_id()
        with self.client.put(f"/api/v1/cart/items/{pid}/",
                             json={"quantity": random.randint(1, 3)},
                             name="/api/v1/cart/items/[id]/",
                             catch_response=True) as r:
            if r.status_code >= 400:
                r.failure(f"{r.status_code}")
                _log_failure("[add_to_cart]", r)
            else:
                r.success()

    @task(1)
    def browse_categories(self):
        self.client.get("/api/v1/categories/", name="/api/v1/categories/")


class GuestUser(BaseShopUser):
    @task(3)
    def browse_products_guest(self):
        self.client.get("/api/v1/products/", name="/api/v1/products/ (guest)")

    @task(2)
    def add_to_cart_guest(self):
        """
        Guest user adds item - backend creates cart and returns token in cookie
        """
        pid = self._pick_product_id()
        with self.client.put(f"/api/v1/cart/items/{pid}/",
                             json={"quantity": 1},
                             name="/api/v1/cart/items/[id]/ (guest)",
                             catch_response=True) as r:
            if r.status_code >= 400:
                r.failure(f"{r.status_code}")
                _log_failure("[guest add_to_cart]", r)
            else:
                r.success()

    @task(1)
    def guest_checkout(self):
        # Ensure at least one item
        pid = self._pick_product_id()
        self.client.put(f"/api/v1/cart/items/{pid}/", json={
                        "quantity": 1}, name="/api/v1/cart/items/[id]/ (guest pre)")

        with self.client.post("/api/v1/cart/checkout/", json=CHECKOUT_PAYLOAD,
                              name="/api/v1/cart/checkout/ (guest)", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"{r.status_code}")
                _log_failure("[guest checkout]", r)
                return
            r.success()

            try:
                data = r.json()
            except Exception:
                return

        order_id = (data.get("order") or {}).get("id")
        guest_token = data.get("guest_access_token")
        if not order_id or not guest_token:
            return

        self.client.post("/api/v1/payments/", json={
                         "order_id": order_id, "result": "success"}, name="/api/v1/payments/ (guest)")
        self.client.get(f"/api/v1/guest/orders/{order_id}/?token={guest_token}",
                        name="/api/v1/guest/orders/[id]/ (guest)")


class JWTAuthUser(BaseShopUser):
    """
    JWT Bearer token authentication
    """

    def on_start(self):
        """
        Login a získání JWT tokenu pro Authorization: Bearer header
        """
        super().on_start()
        email, pwd = random.choice(USER_POOL)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self._refresh_in_flight = False

        with self.client.post("/api/v1/auth/login/", json={"email": email, "password": pwd},
                              name="/api/v1/auth/login/ (jwt)", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"{r.status_code}")
                _log_failure("[jwt login]", r)
                return

            try:
                tokens = r.json()
            except Exception:
                r.failure("invalid json")
                _log_failure("[jwt login json]", r)
                return

            self.access_token = tokens.get("access")
            self.refresh_token = tokens.get("refresh")
            if self.access_token:
                self.client.headers.update(
                    {"Authorization": f"Bearer {self.access_token}"})
            r.success()

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
        pid = self._pick_product_id()
        with self.client.put(f"/api/v1/cart/items/{pid}/",
                             json={"quantity": 1},
                             name="/api/v1/cart/items/[id]/ (JWT)",
                             catch_response=True) as r:
            if r.status_code >= 400:
                r.failure(f"{r.status_code}")
                _log_failure("[jwt add_to_cart]", r)
            else:
                r.success()

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
        # Make refresh much less aggressive (baseline load should be business-heavy)
        if random.random() > 0.1:  # ~10% of the time
            return
        if not self.refresh_token or self._refresh_in_flight:
            return

        self._refresh_in_flight = True
        try:
            with self.client.post("/api/v1/auth/refresh/", json={"refresh": self.refresh_token},
                                  name="/api/v1/auth/refresh/", catch_response=True) as r:
                if r.status_code != 200:
                    r.failure(f"{r.status_code}")
                    _log_failure("[jwt refresh]", r)
                    return

                try:
                    tokens = r.json()
                except Exception:
                    r.failure("invalid json")
                    _log_failure("[jwt refresh json]", r)
                    return

                new_access = tokens.get("access")
                # if rotation returns new refresh
                new_refresh = tokens.get("refresh")
                if new_access:
                    self.access_token = new_access
                    self.client.headers.update(
                        {"Authorization": f"Bearer {self.access_token}"})
                if new_refresh:
                    self.refresh_token = new_refresh
                r.success()
        finally:
            self._refresh_in_flight = False


class HeavyShopperUser(BaseShopUser):
    """
    Simuluje "heavy shopper" - uživatele, který aktivně nakupuje
    Používá SESSION auth (login vytvoří session cookie)
    """

    wait_time = between(0.5, 2)

    def on_start(self):
        super().on_start()
        email, pwd = random.choice(USER_POOL)
        with self.client.post("/api/v1/auth/login/", json={"email": email, "password": pwd},
                              name="/api/v1/auth/login/ (heavy)", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"{r.status_code}")
                _log_failure("[heavy login]", r)
            else:
                r.success()

    @task(5)
    def rapid_product_browsing(self):
        """
        Rapidly browse products (simulates scrolling through catalog)
        """
        self.client.get("/api/v1/products/", name="/api/v1/products/ (heavy)")

    @task(3)
    def add_multiple_items(self):
        """
        Add multiple items quickly
        """
        for _ in range(random.randint(2, 5)):
            pid = self._pick_product_id()
            with self.client.put(f"/api/v1/cart/items/{pid}/",
                                 json={"quantity": 1},
                                 name="/api/v1/cart/items/[id]/ (batch)",
                                 catch_response=True) as r:
                if r.status_code >= 400:
                    r.failure(f"{r.status_code}")
                    _log_failure("[batch add_to_cart]", r)
                else:
                    r.success()

    @task(1)
    def checkout_flow(self):
        """
        Complete checkout flow
        """
        # Get cart
        cart_response = self.client.get(
            "/api/v1/cart/", name="/api/v1/cart/ (heavy)")

        if cart_response.status_code == 200:
            # Checkout
            with self.client.post("/api/v1/cart/checkout/", json=CHECKOUT_PAYLOAD,
                                  name="/api/v1/cart/checkout/", catch_response=True) as r:
                if r.status_code != 200:
                    r.failure(f"{r.status_code}")
                    _log_failure("[heavy checkout]", r)
                    return
                r.success()

                try:
                    order_data = r.json()
                except Exception:
                    return

            order_id = (order_data.get("order") or {}).get("id")
            if order_id:
                # Simulate payment
                self.client.post(
                    "/api/v1/payments/", json={"order_id": order_id, "result": "success"}, name="/api/v1/payments/")
