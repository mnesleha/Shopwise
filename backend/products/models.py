from django.db import models

# Create your models here.


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def is_sellable(self) -> bool:
        return self.is_active and self.stock_quantity > 0

    def __str__(self):
        return self.name
