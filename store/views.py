import logging
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.db import DatabaseError, transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.http import FileResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404, redirect, render
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .forms import (
    CategoryForm,
    CustomerForm,
    ProductForm,
    PurchaseItemForm,
    PurchasesForm,
    ReceiptPaymentForm,
    SalesForm,
    SalesItemForm,
    SignupForm,
    StoreForm,
)
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

logger = logging.getLogger(__name__)

SIGNUP_CODE_MAX_ATTEMPTS = 5
SIGNUP_CODE_ATTEMPT_WINDOW = 15 * 60


def _signup_code_attempt_key(request):
    remote_address = request.META.get("REMOTE_ADDR", "unknown")
    return f"signup-code-attempts:{remote_address}"


def _record_signup_code_attempt(cache_key):
    if not cache.add(cache_key, 1, timeout=SIGNUP_CODE_ATTEMPT_WINDOW):
        try:
            cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=SIGNUP_CODE_ATTEMPT_WINDOW)


@require_http_methods(["GET", "POST"])
def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST":
        attempt_key = _signup_code_attempt_key(request)
        if cache.get(attempt_key, 0) >= SIGNUP_CODE_MAX_ATTEMPTS:
            form.add_error(
                "invitation_code",
                "Too many failed code attempts. Try again in 15 minutes.",
            )
        elif form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    invitation_claimed = SignupInvitation.objects.filter(
                        code=form.cleaned_data["invitation_code"],
                        used_at__isnull=True,
                    ).update(used_by=user, used_at=timezone.now())
                    if invitation_claimed != 1:
                        raise ValidationError(
                            "This five-digit invitation code is invalid or has already been used."
                        )
            except ValidationError as error:
                form.add_error("invitation_code", error)
                _record_signup_code_attempt(attempt_key)
            else:
                cache.delete(attempt_key)
                if not request.user.is_authenticated:
                    login(request, user)
                messages.success(request, "Your account has been created.")
                return redirect("home")
        elif form.errors.get("invitation_code"):
            _record_signup_code_attempt(attempt_key)

    return render(request, "signup.html", {"form": form})


@login_required
def home(request):
    inventory_summary = Inventory.objects.aggregate(total_units=Sum("quantity"))
    sales_summary = Sales.objects.aggregate(total_revenue=Sum("total_amount"))
    context = {
        "customer_count": Customer.objects.count(),
        "product_count": Product.objects.count(),
        "category_count": Category.objects.count(),
        "store_count": Store.objects.count(),
        "sales_count": Sales.objects.count(),
        "purchase_count": Purchases.objects.count(),
        "inventory_units": inventory_summary["total_units"] or 0,
        "total_revenue": sales_summary["total_revenue"] or Decimal("0.00"),
        "recent_sales": Sales.objects.select_related("customer").order_by("-sale_date", "-pk")[:5],
        "low_stock": Inventory.objects.select_related("product", "store")
        .filter(quantity__lte=10)
        .order_by("quantity", "product__item")[:5],
    }
    return render(request, "dashboard_index.html", context)


@login_required
def about(request):
    return render(request, "about.html")


@require_http_methods(["GET", "POST"])
def crud_view(request, form_class, model, template_name, title, description, success_message):
    is_delete_request = request.method == "POST" and "delete_pk" in request.POST
    database_failure = False

    if is_delete_request:
        record = get_object_or_404(model, pk=request.POST["delete_pk"])
        try:
            record.delete()
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
            database_failure = True
        except DatabaseError:
            logger.exception("Database error deleting %s record", title)
            messages.error(request, f"{title} could not be deleted because the database rejected the change.")
            database_failure = True
        else:
            return redirect(f"{request.path}?view=1&deleted=1")

    edit_pk = request.POST.get("edit_pk") if request.method == "POST" and not is_delete_request else request.GET.get("edit")
    instance = get_object_or_404(model, pk=edit_pk) if edit_pk else None
    form_data = request.POST if request.method == "POST" and not is_delete_request else None
    form = form_class(form_data, instance=instance)
    if request.method == "POST" and not is_delete_request:
        if form.is_valid():
            try:
                form.save()
            except ValidationError as error:
                form.add_error(None, error)
                messages.error(request, " ".join(error.messages))
            except DatabaseError:
                logger.exception("Database error saving %s record", title)
                messages.error(request, f"{title} could not be saved because the database rejected the change.")
                database_failure = True
            else:
                messages.success(
                    request,
                    f"{title} updated successfully." if instance else success_message,
                )
                return redirect(f"{request.path}?saved=1")
        else:
            errors = []
            for field_name, field_errors in form.errors.items():
                label = form[field_name].label if field_name in form.fields else "Form"
                errors.extend(f"{label}: {error}" for error in field_errors)
            messages.error(request, "Please correct the form: " + " ".join(errors))

    show_records = True
    show_form = (
        instance is not None
        or (request.method == "GET" and request.GET.get("add") == "1")
        or (request.method == "POST" and not is_delete_request)
    )
    if show_records and request.GET.get("deleted") == "1":
        messages.success(request, f"{title} deleted successfully.")
    records = model.objects.select_related().all().order_by(*(model._meta.ordering or ("pk",)))
    if show_records and model is Customer:
        records = records.annotate(
            amount_spent=Coalesce(
                Sum("sales__total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    customer_spending = list(
        Customer.objects.annotate(
            amount_spent=Coalesce(
                Sum("sales__total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        ).values("pk", "amount_spent")
    )
    return render(request, template_name, {
        "form": form,
        "title": title,
        "description": description,
        "editing": instance is not None,
        "show_form": show_form,
        "show_records": show_records,
        "records": records,
        "customer_spending": customer_spending,
    })


@login_required
def add_category_view(request):
    return crud_view(request, CategoryForm, Category, "category.html", "Category",
                     "Product categories used by the store.", "Category saved successfully.")


@login_required
def add_customer_view(request):
    return crud_view(request, CustomerForm, Customer, "customer.html", "Customer",
                     "Registered customers and their spending.", "Customer saved successfully.")


@login_required
def add_product_view(request):
    return crud_view(request, ProductForm, Product, "product.html", "Product",
                     "Products stocked and sold by the store.", "Product saved successfully.")


@login_required
def add_store_view(request):
    return crud_view(request, StoreForm, Store, "store.html", "Store", "Store branches.",
                     "Store saved successfully.")


@login_required
@require_http_methods(["GET"])
def update_inventory_view(request):
    records = Inventory.objects.select_related("product", "store").order_by(
        "product__item", "store__store_name"
    )
    return render(request, "inventory.html", {"records": records})


@login_required
def add_purchase_view(request):
    return crud_view(request, PurchasesForm, Purchases, "purchases.html", "Purchases",
                     "Orders placed with suppliers.", "Purchase saved successfully.")


@login_required
def add_purchase_item_view(request):
    return crud_view(request, PurchaseItemForm, PurchaseItem, "purchase_item.html", "Purchase Item",
                     "Products included in each purchase.", "Purchase item saved successfully.")


@login_required
def add_sales_view(request):
    return crud_view(request, SalesForm, Sales, "sales.html", "Sales",
                     "Sales transactions completed with customers.", "Sale saved successfully.")


@login_required
@require_http_methods(["GET", "POST"])
def sale_receipt(request, pk):
    sale = get_object_or_404(
        Sales.objects.select_related("customer").prefetch_related("items__product", "items__store"),
        pk=pk,
    )
    items = list(sale.items.all())
    balance = sale.amount_paid - sale.total_amount
    payment_recorded = sale.total_amount > 0 and sale.amount_paid >= sale.total_amount
    payment_form = ReceiptPaymentForm(
        initial={"amount_paid": sale.amount_paid} if sale.amount_paid > 0 else None,
        total_amount=sale.total_amount,
    )
    if request.method == "POST" and "save_payment" in request.POST:
        payment_form = ReceiptPaymentForm(request.POST, total_amount=sale.total_amount)
        if payment_form.is_valid():
            sale.amount_paid = payment_form.cleaned_data["amount_paid"]
            sale.save(update_fields=("amount_paid",))
            messages.success(request, "Payment saved and balance updated.")
            return redirect("sale_receipt", pk=sale.pk)
    elif request.method == "POST" and "print_receipt" in request.POST:
        if not payment_recorded:
            messages.error(request, "Enter and save an amount that covers the total before printing this receipt.")
            return redirect("sale_receipt", pk=sale.pk)
        receipt_directory = Path(settings.BASE_DIR) / "store" / "static" / "receipts"
        receipt_directory.mkdir(parents=True, exist_ok=True)
        pdf_path = receipt_directory / f"receipt-{sale.pk}.pdf"
        page_width, page_height = letter
        pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
        logo_path = Path(settings.BASE_DIR) / "store" / "static" / "assets" / "dashboard" / "images" / "logo1.png"
        pdf.drawImage(ImageReader(str(logo_path)), page_width / 2 - 35, page_height - 105,
                      width=70, height=70, preserveAspectRatio=True, mask="auto", anchor="c")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(page_width / 2, page_height - 126, "SENAMAT SUPERMARKET")
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(page_width / 2, page_height - 145, f"Receipt #{sale.pk}")
        pdf.drawString(48, page_height - 175, f"Customer: {sale.customer.customer_name}")
        pdf.drawString(48, page_height - 191, f"Date and time: {timezone.localtime(sale.sale_date):%d %b %Y, %I:%M %p}")

        table_top = page_height - 225
        pdf.setFillColorRGB(0.91, 0.94, 0.98)
        pdf.rect(42, table_top - 8, page_width - 84, 22, fill=1, stroke=0)
        pdf.setFillColorRGB(0.12, 0.16, 0.22)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(48, table_top, "Goods purchased")
        pdf.drawRightString(350, table_top, "Qty")
        pdf.drawRightString(450, table_top, "Unit price")
        pdf.drawRightString(page_width - 48, table_top, "Amount")
        y = table_top - 23
        pdf.setFont("Helvetica", 9)
        for item in items:
            if y < 115:
                pdf.showPage()
                y = page_height - 55
                pdf.setFont("Helvetica", 9)
            line_amount = item.quantity * item.unit_price
            pdf.drawString(48, y, item.product.item[:42])
            pdf.drawRightString(350, y, str(item.quantity))
            pdf.drawRightString(450, y, f"{item.unit_price:.2f} shs")
            pdf.drawRightString(page_width - 48, y, f"{line_amount:.2f} shs")
            y -= 19

        y -= 7
        pdf.setStrokeColorRGB(0.82, 0.86, 0.91)
        pdf.line(48, y, page_width - 48, y)
        y -= 20
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawRightString(page_width - 48, y, f"Total amount: {sale.total_amount:.2f} shs")
        y -= 18
        pdf.drawRightString(page_width - 48, y, f"Amount paid: {sale.amount_paid:.2f} shs")
        y -= 18
        pdf.drawRightString(page_width - 48, y, f"Balance: {balance:.2f} shs")
        pdf.save()
        return FileResponse(open(pdf_path, "rb"), content_type="application/pdf", as_attachment=False)

    return render(request, "receipt.html", {
        "sale": sale,
        "items": items,
        "balance": balance,
        "payment_form": payment_form,
        "payment_recorded": payment_recorded,
        "payment_entered": sale.amount_paid > 0,
    })


@login_required
def add_sales_item_view(request):
    return crud_view(request, SalesItemForm, SalesItem, "sales_item.html", "Sales Item",
                     "Products included in each sale.", "Sales item saved successfully.")