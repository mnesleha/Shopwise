"""
Locust test - Product API load testing (read-heavy scenario)
"""
from locust import HttpUser, task, between
import random


class ProductBrowser(HttpUser):
    """
    Testuje pouze product API - typický read-heavy scenario
    Simuluje uživatele, kteří jen browsují produkty bez nákupu
    """
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        self.client.headers.update({"Accept": "application/json"})
    
    @task(5)
    def list_products(self):
        """
        GET /api/v1/products/ - nejvíce zatížený endpoint
        """
        self.client.get("/api/v1/products/", name="GET /api/v1/products/")
    
    @task(3)
    def get_product_detail(self):
        """
        GET /api/v1/products/{id}/ - druhý nejčastější request
        """
        product_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/products/{product_id}/",
            name="GET /api/v1/products/[id]/"
        )
    
    @task(1)
    def list_categories(self):
        """
        GET /api/v1/categories/
        """
        self.client.get("/api/v1/categories/", name="GET /api/v1/categories/")


class ProductSearcher(HttpUser):
    """
    Testuje product filtering/searching
    """
    
    wait_time = between(1, 3)
    
    def on_start(self):
        self.client.headers.update({"Accept": "application/json"})
    
    @task(4)
    def search_products(self):
        """
        Search products by name (most common use case)
        """
        search_terms = ["MOUSE", "KEYBOARD", "HEADSET", "MONITOR", "LAPTOP", "CABLE"]
        term = random.choice(search_terms)
        self.client.get(
            f"/api/v1/products/?search={term}",
            name="GET /api/v1/products/?search=[term]"
        )
    
    @task(3)
    def search_by_category(self):
        """
        Filter products by category
        """
        category_id = random.randint(1, 10)
        self.client.get(
            f"/api/v1/products/?category={category_id}",
            name="GET /api/v1/products/?category=[id]"
        )
    
    @task(2)
    def search_active_products(self):
        """
        Filter only active products
        """
        self.client.get(
            "/api/v1/products/?is_active=true",
            name="GET /api/v1/products/?is_active=true"
        )
    
    @task(1)
    def pagination_test(self):
        """
        Test pagination
        """
        page = random.randint(1, 5)
        self.client.get(
            f"/api/v1/products/?page={page}",
            name="GET /api/v1/products/?page=[n]"
        )
