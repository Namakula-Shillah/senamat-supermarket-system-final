from decimal import Decimal
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Lower

# Create your models here.
class Category(models.Model):
    category_name = models.CharField(max_length=50)

    class Meta:
        ordering = ("category_name",)
        constraints = [
            models.UniqueConstraint(Lower("category_name"), name="unique_category_name_ci"),
        ]

    def __str__(self):
        return self.category_name
    

class Customer(models.Model):
    customer_name = models.CharField(max_length=100)
    contact = models.CharField(max_length=30, blank=True)
    gender = models.CharField(
        max_length=10,
        blank=True,
        choices=(("Female", "Female"), ("Male", "Male"), ("Other", "Other")),
    )
    address = models.TextField(blank=True)

    class Meta:
        ordering = ("customer_name",)

    def __str__(self):
        return self.customer_name

class Product(models.Model):
    item = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    brand = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ("item",)

    def __str__(self):
        return self.item

class Store(models.Model):
    store_name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ("store_name",)

    def __str__(self):
        return self.store_name


class SignupInvitation(models.Model):
    code = models.CharField(
        max_length=5,
        unique=True,
        editable=False,
        validators=[RegexValidator(r"^[0-9]{5}$", "Invitation codes must be five digits.")],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_signup_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_signup_invitations",
    )
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            if type(self).objects.count() >= 100_000:
                raise ValidationError("No unused five-digit invitation codes remain.")
            while True:
                code = f"{secrets.randbelow(100_000):05d}"
                if not type(self).objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ("product__item", "store__store_name")
        constraints = [
            models.UniqueConstraint(fields=("product", "store"), name="unique_inventory_product_store"),
        ]

    def __str__(self):
        return f"{self.product} at {self.store} ({self.quantity})"



def _adjust_inventory(product_id, store_id, quantity_delta):
    if store_id is None or quantity_delta == 0:
        return

    inventory = Inventory.objects.select_for_update().filter(
        product_id=product_id,
        store_id=store_id,
    ).first()
    if inventory is None:
        if quantity_delta < 0:
            raise ValidationError("There is no stock for this product at the selected store.")
        inventory = Inventory(product_id=product_id, store_id=store_id, quantity=0)

    updated_quantity = inventory.quantity + quantity_delta
    if updated_quantity < 0:
        raise ValidationError("This change would reduce the store's inventory below zero.")
    inventory.quantity = updated_quantity
    inventory.save()


def _line_total():
    return ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

class Purchases(models.Model):
    
    purchase_date = models.DateTimeField(auto_now_add=True)
    supplier_name = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ("purchase_date", "pk")

    def __str__(self):
        return f"{self.supplier_name} ({self.pk})"

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            for item in self.items.select_for_update():
                _adjust_inventory(item.product_id, item.store_id, -item.quantity)
            return super().delete(*args, **kwargs)

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchases, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="purchase_items", null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ("purchase_id", "product__item", "pk")

    def __str__(self):
        return f"{self.quantity} x {self.product} (purchase #{self.purchase_id})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            previous = type(self).objects.select_for_update().filter(pk=self.pk).first() if self.pk else None
            if self.store_id is None:
                raise ValidationError({"store": "Choose a store for this purchase item."})
            old_purchase_id = previous.purchase_id if previous else None
            if previous:
                _adjust_inventory(previous.product_id, previous.store_id, -previous.quantity)
            super().save(*args, **kwargs)
            _adjust_inventory(self.product_id, self.store_id, self.quantity)
            purchase_ids = {self.purchase_id}
            if old_purchase_id:
                purchase_ids.add(old_purchase_id)
            for purchase_id in purchase_ids:
                total = type(self).objects.filter(purchase_id=purchase_id).aggregate(total=Sum(_line_total()))["total"]
                Purchases.objects.filter(pk=purchase_id).update(total_amount=total or Decimal("0.00"))

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            _adjust_inventory(self.product_id, self.store_id, -self.quantity)
            result = super().delete(*args, **kwargs)
            total = type(self).objects.filter(purchase_id=self.purchase_id).aggregate(total=Sum(_line_total()))["total"]
            Purchases.objects.filter(pk=self.purchase_id).update(total_amount=total or Decimal("0.00"))
            return result

class Sales(models.Model):
    sale_date = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ("sale_date", "pk")

    def __str__(self):
        return f"{self.customer} ({self.pk})"

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            for item in self.items.select_for_update():
                _adjust_inventory(item.product_id, item.store_id, item.quantity)
            return super().delete(*args, **kwargs)

class SalesItem(models.Model):
    sale = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="sales_items", null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ("sale_id", "product__item", "pk")

    def __str__(self):
        return f"{self.quantity} x {self.product} (sale #{self.sale_id})"

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        with transaction.atomic():
            previous = type(self).objects.select_for_update().filter(pk=self.pk).first() if self.pk else None
            if self.store_id is None:
                raise ValidationError({"store": "Choose a store for this sales item."})
            old_sale_id = previous.sale_id if previous else None
            if previous:
                _adjust_inventory(previous.product_id, previous.store_id, previous.quantity)
            _adjust_inventory(self.product_id, self.store_id, -self.quantity)
            super().save(*args, **kwargs)
            sale_ids = {self.sale_id}
            if old_sale_id:
                sale_ids.add(old_sale_id)
            for sale_id in sale_ids:
                total = type(self).objects.filter(sale_id=sale_id).aggregate(total=Sum(_line_total()))["total"]
                Sales.objects.filter(pk=sale_id).update(total_amount=total or Decimal("0.00"))

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            _adjust_inventory(self.product_id, self.store_id, self.quantity)
            result = super().delete(*args, **kwargs)
            total = type(self).objects.filter(sale_id=self.sale_id).aggregate(total=Sum(_line_total()))["total"]
            Sales.objects.filter(pk=self.sale_id).update(total_amount=total or Decimal("0.00"))
            return result
