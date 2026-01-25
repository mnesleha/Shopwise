"""
Locust test - Checkout flow performance (write-heavy scenario)
"""
from locust import HttpUser, task, between, SequentialTaskSet
import random


class CheckoutFlowTaskSet(SequentialTaskSet):
    """
    Sequential task set - simuluje kompletní checkout flow v pořadí
    """
    
    @task
    def step_1_browse_products(self):
        """
        Krok 1: Prohlížení produktů
        """
        self.client.get("/api/v1/products/")
    
    @task
    def step_2_add_first_item(self):
        """
        Krok 2: Přidání prvního produktu do košíku
        """
        product_id = random.randint(1, 50)
        self.product_ids = [product_id]
        
        response = self.client.put(
            f"/api/v1/cart/items/{product_id}/",
            json={"quantity": 2},
            name="PUT /api/v1/cart/items/[id]/ (first)"
        )
        
        if response.status_code != 200:
            print(f"Failed to add first item: {response.status_code}")
    
    @task
    def step_3_add_second_item(self):
        """
        Krok 3: Přidání druhého produktu
        """
        product_id = random.randint(51, 100)
        self.product_ids.append(product_id)
        
        self.client.put(
            f"/api/v1/cart/items/{product_id}/",
            json={"quantity": 1},
            name="PUT /api/v1/cart/items/[id]/ (second)"
        )
    
    @task
    def step_4_view_cart(self):
        """
        Krok 4: Zobrazení košíku před checkoutem
        """
        self.client.get("/api/v1/cart/")
    
    @task
    def step_5_checkout(self):
        """
        Krok 5: Checkout - vytvoření objednávky
        """
        response = self.client.post("/api/v1/cart/checkout/")
        
        if response.status_code == 200:
            data = response.json()
            self.order_id = data.get("order", {}).get("id")
            print(f"Checkout successful, order ID: {self.order_id}")
        else:
            print(f"Checkout failed: {response.status_code}")
            self.order_id = None
    
    @task
    def step_6_payment(self):
        """
        Krok 6: Platba
        """
        if not hasattr(self, 'order_id') or not self.order_id:
            print("No order ID, skipping payment")
            return
        
        response = self.client.post("/api/v1/payments/", json={
            "order_id": self.order_id,
            "result": "success"
        })
        
        if response.status_code == 201:
            print(f"Payment successful for order {self.order_id}")
        else:
            print(f"Payment failed: {response.status_code}")
    
    @task
    def step_7_view_order(self):
        """
        Krok 7: Zobrazení vytvořené objednávky
        """
        if not hasattr(self, 'order_id') or not self.order_id:
            print("No order ID, skipping view order")
            return
        
        self.client.get(f"/api/v1/orders/{self.order_id}/")
        
        # Stop the sequence - user completed checkout
        self.interrupt()


class CheckoutUser(HttpUser):
    """
    User simulující kompletní checkout flow
    """
    
    tasks = [CheckoutFlowTaskSet]
    wait_time = between(2, 5)
    
    def on_start(self):
        """
        Login před začátkem testu
        """
        self.client.headers.update({"Accept": "application/json"})
        
        # Login as test user
        login_response = self.client.post("/api/v1/auth/login/", json={
            "email": "customer_2@example.com",
            "password": "TestPassword123!"
        })
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")


class FailedPaymentUser(HttpUser):
    """
    Testuje scénář s failed payment - edge case
    """
    
    wait_time = between(3, 7)
    
    def on_start(self):
        self.client.headers.update({"Accept": "application/json"})
        
        login_response = self.client.post("/api/v1/auth/login/", json={
            "email": "customer_2@example.com",
            "password": "TestPassword123!"
        })
        
        if login_response.status_code != 200:
            print(f"Login failed")
    
    @task
    def checkout_with_failed_payment(self):
        """
        Checkout následovaný failed platbou
        """
        # Add item to cart
        product_id = random.randint(1, 50)
        self.client.put(f"/api/v1/cart/items/{product_id}/", json={"quantity": 1})
        
        # Checkout
        checkout_response = self.client.post("/api/v1/cart/checkout/")
        
        if checkout_response.status_code == 200:
            order_id = checkout_response.json().get("order", {}).get("id")
            
            # Failed payment
            self.client.post("/api/v1/payments/", json={
                "order_id": order_id,
                "result": "fail"  # Simulates payment failure
            }, name="POST /api/v1/payments/ (failed)")
