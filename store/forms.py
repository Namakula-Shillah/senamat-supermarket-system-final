from decimal import Decimal

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import (
    Category,
    Customer,
    Inventory,
    Product,
    PurchaseItem,
    Purchases,
    Sales,
    SalesItem,
    SignupInvitation,
    Store,
)


class SignupForm(UserCreationForm):
    invitation_code = forms.RegexField(
        regex=r"^[0-9]{5}$",
        label="Five-digit admin code",
        min_length=5,
        max_length=5,
        help_text="Enter the one-time five-digit code provided by a superuser.",
        widget=forms.TextInput(attrs={
            "autocomplete": "off",
            "inputmode": "numeric",
            "pattern": "[0-9]{5}",
        }),
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(("username", "invitation_code", "password1", "password2"))

    def clean_invitation_code(self):
        code = self.cleaned_data["invitation_code"].strip()
        if not SignupInvitation.objects.filter(code=code, used_at__isnull=True).exists():
            raise forms.ValidationError("This five-digit invitation code is invalid or has already been used.")
        return code


class StoreModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class CategoryForm(StoreModelForm):
    class Meta:
        model = Category
        fields = "__all__"

    def clean_category_name(self):
        category_name = self.cleaned_data["category_name"].strip()
        if Category.objects.filter(category_name__iexact=category_name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This category already exists.")
        return category_name


class CustomerForm(StoreModelForm):
    class Meta:
        model = Customer
        fields = ("customer_name", "contact", "gender", "address")


class ProductForm(StoreModelForm):
    unit_price = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)
    category = forms.ModelChoiceField(queryset=Category.objects.order_by("category_name"))

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].required = True
        self.fields["color"].required = True
        self.fields["model"].required = True


class StoreForm(StoreModelForm):
    class Meta:
        model = Store
        fields = "__all__"

    def clean_store_name(self):
        store_name = self.cleaned_data["store_name"].strip()
        if Store.objects.filter(store_name__iexact=store_name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This store already exists.")
        return store_name


class PurchasesForm(StoreModelForm):
    class Meta:
        model = Purchases
        fields = ("supplier_name",)


class PurchaseItemForm(StoreModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.order_by("item"),
        label="Product",
        empty_label="Select a product",
    )
    quantity = forms.IntegerField(min_value=1)
    unit_price = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)
    store = forms.ModelChoiceField(queryset=Store.objects.order_by("store_name"), required=True)

    class Meta:
        model = PurchaseItem
        fields = ("purchase", "product", "store", "quantity", "unit_price")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields((
            "purchase",
            "product",
            "store",
            "quantity",
            "unit_price",
        ))


class SalesForm(StoreModelForm):
    class Meta:
        model = Sales
        fields = ("customer",)


class ReceiptPaymentForm(forms.Form):
    amount_paid = forms.DecimalField(
        label="Amount paid by customer",
        min_value=Decimal("0.01"),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "step": "0.01",
            "placeholder": "Enter amount paid",
            "data-receipt-payment": "",
        }),
    )

    def __init__(self, *args, total_amount=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_amount = total_amount

    def clean_amount_paid(self):
        amount_paid = self.cleaned_data["amount_paid"]
        if self.total_amount is not None and amount_paid < self.total_amount:
            raise forms.ValidationError("Amount paid must cover the total amount.")
        return amount_paid


class SalesItemForm(StoreModelForm):
    quantity = forms.IntegerField(min_value=1)
    unit_price = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2)
    store = forms.ModelChoiceField(queryset=Store.objects.order_by("store_name"), required=True)
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(
            category__isnull=False,
            brand__gt="",
            color__gt="",
            model__gt="",
        ).order_by("item")
    )

    class Meta:
        model = SalesItem
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        store = cleaned_data.get("store")
        quantity = cleaned_data.get("quantity")
        if not (product and store and quantity):
            return cleaned_data

        inventory = Inventory.objects.filter(product=product, store=store).first()
        available = inventory.quantity if inventory else 0
        if self.instance.pk and self.instance.product_id == product.pk and self.instance.store_id == store.pk:
            available += self.instance.quantity
        if quantity > available:
            self.add_error("quantity", "The selected store does not have enough stock.")
        return cleaned_data


