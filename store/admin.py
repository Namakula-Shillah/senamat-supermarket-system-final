from django.contrib import admin
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import (
    Category,
    Customer,
    Product,
    Store,
    Inventory,
    Purchases,
    PurchaseItem,
    Sales,
    SalesItem,
    SignupInvitation,
)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name',)


class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'amount_spent')
    search_fields = ('customer_name', 'contact')
    list_filter = ('gender',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            amount_spent=Coalesce(
                Sum('sales__total_amount'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )

    @admin.display(description='Amount spent', ordering='amount_spent')
    def amount_spent(self, customer):
        return customer.amount_spent


class ProductAdmin(admin.ModelAdmin):
    list_display = ('item', 'brand', 'category', 'unit_price')
    search_fields = ('item', 'brand', 'model')
    list_filter = ('category',)


class StoreAdmin(admin.ModelAdmin):
    list_display = ('store_name',)
    search_fields = ('store_name',)


class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'store', 'quantity')
    list_filter = ('store',)
    search_fields = ('product__item',)


class PurchasesAdmin(admin.ModelAdmin):
    list_display = ('supplier_name', 'purchase_date', 'total_amount')
    search_fields = ('supplier_name',)
    list_filter = ('purchase_date',)
    exclude = ('total_amount',)


class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'product', 'quantity', 'unit_price')
    search_fields = ('product__item', 'purchase__supplier_name')
    list_filter = ('purchase',)


class SalesAdmin(admin.ModelAdmin):
    list_display = ('customer', 'sale_date', 'total_amount')
    search_fields = ('customer__customer_name',)
    list_filter = ('sale_date',)
    exclude = ('total_amount',)


class SalesItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product', 'quantity', 'unit_price')
    search_fields = ('product__item', 'sale__customer__customer_name')
    list_filter = ('sale',)


class SignupInvitationAdmin(admin.ModelAdmin):
    list_display = ('code', 'created_by', 'created_at', 'used_by', 'used_at')
    readonly_fields = ('code', 'created_by', 'created_at', 'used_by', 'used_at')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Category, CategoryAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Store, StoreAdmin)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(Purchases, PurchasesAdmin)
admin.site.register(PurchaseItem, PurchaseItemAdmin)
admin.site.register(Sales, SalesAdmin)
admin.site.register(SalesItem, SalesItemAdmin)
admin.site.register(SignupInvitation, SignupInvitationAdmin)
