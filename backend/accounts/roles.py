from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    WAREHOUSE_MANAGER = "warehouse_manager", "Warehouse Manager"
    SUPPORT = "support", "Customer Support"
