import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Sum
from django.test import Client, TestCase, override_settings

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


class ModelPageTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username="cashier", password="test-password-123")
		self.client.force_login(self.user)
		self.category = Category.objects.create(category_name="Electronics")
		self.customer = Customer.objects.create(customer_name="Ada", contact="0700000000")
		self.product = Product.objects.create(
			item="Tea",
			unit_price="2.50",
			brand="Fresh",
			color="Green",
			model="T1",
			category=self.category,
		)
		self.other_product = Product.objects.create(
			item="Soap", unit_price="3.00", brand="Fresh", color="White",
			model="S1", category=self.category,
		)
		self.store = Store.objects.create(store_name="Kampala")
		self.other_store = Store.objects.create(store_name="Jinja")
		self.purchase = Purchases.objects.create(supplier_name="Supplier")
		self.sale = Sales.objects.create(customer=self.customer)
		Inventory.objects.create(product=self.product, store=self.store, quantity=4)
		PurchaseItem.objects.create(
			purchase=self.purchase, product=self.product, store=self.store,
			quantity=2, unit_price="2.50",
		)
		SalesItem.objects.create(
			sale=self.sale, product=self.product, store=self.store,
			quantity=1, unit_price="2.50",
		)

	def test_model_pages_render_database_records(self):
		for path in (
			"/category/",
			"/customer/",
			"/product/",
			"/purchase-item/",
			"/purchases/",
			"/sales-item/",
			"/sales/",
			"/store/",
		):
			with self.subTest(path=path):
				response = self.client.get(path)
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, "Records")
				self.assertContains(response, 'href="/static/style.css"')
				self.assertFalse(response.context["show_form"])
				self.assertTrue(response.context["show_records"])
				self.assertTrue(response.context["form"].fields)
				self.assertTrue(response.context["records"].exists())
				self.assertContains(response, "data-form-modal")
				self.assertContains(response, "data-open-form")
				self.assertContains(response, "form-modal-back")
				self.assertContains(response, "icon-arrow-left")
				self.assertContains(response, ">Back</span>")
				self.assertNotContains(response, "View Categories")
				self.assertContains(response, 'class="ti ti-edit"')
				self.assertContains(response, 'class="ti ti-trash"')
				self.assertContains(response, 'href="/static/assets/dashboard/fonts/tabler-icons.min.css"')
				self.assertContains(response, 'src="/static/assets/dashboard/images/logo1.png"')
				self.assertContains(response, "Stores")
				self.assertContains(response, 'class="sidebar-footer"')
				self.assertContains(response, 'aria-label="Log out"')

				add_response = self.client.get(path, {"add": "1"})
				self.assertTrue(add_response.context["show_form"])
				self.assertTrue(add_response.context["show_records"])
				self.assertContains(add_response, 'aria-hidden="false"')

				view_response = self.client.get(path, {"view": "1"})
				self.assertFalse(view_response.context["show_form"])
				self.assertTrue(view_response.context["show_records"])
				self.assertTrue(view_response.context["records"].exists())
				self.assertContains(view_response, "data-open-form")

	def test_inventory_is_read_only_and_shows_all_stock_by_default(self):
		response = self.client.get("/inventory/")

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Inventory Records")
		self.assertContains(response, "Tea")
		self.assertContains(response, "Kampala")
		self.assertNotContains(response, "Add New Inventory")
		self.assertNotContains(response, "View Inventory")
		self.assertNotContains(response, "Edit")
		self.assertEqual(len(response.context["records"]), 1)

		post_response = self.client.post("/inventory/", {
			"product": self.other_product.pk,
			"store": self.other_store.pk,
			"quantity": 3,
		})
		self.assertEqual(post_response.status_code, 405)

	def test_home_and_login_pages_link_stylesheet(self):
		for path in ("/", "/login/"):
			with self.subTest(path=path):
				response = self.client.get(path)
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, 'href="/static/style.css"')
				self.assertContains(response, 'href="/static/dashboard.css?v=12"')
				self.assertContains(response, "Log In")
				self.assertContains(response, 'src="/static/assets/dashboard/images/logo1.png"')

		signup_response = Client().get("/signup/")
		self.assertContains(signup_response, 'href="/static/dashboard.css?v=12"')

		page_response = self.client.get("/category/")
		self.assertContains(page_response, 'src="/static/app.js?v=9"')
		self.assertContains(page_response, "Add New Category")
		self.assertNotContains(page_response, "View Categories")

	def test_dashboard_uses_live_store_metrics_and_dashboard_assets(self):
		response = self.client.get("/home/")

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "dashboard_index.html")
		self.assertContains(response, 'href="/static/dashboard.css?v=13"')
		self.assertContains(response, 'href="/static/assets/dashboard/fonts/feather.css"')
		self.assertEqual(response.context["customer_count"], 1)
		self.assertEqual(response.context["product_count"], 2)
		self.assertEqual(response.context["sales_count"], 1)
		self.assertEqual(response.context["total_revenue"], Decimal("2.50"))
		self.assertEqual(response.context["inventory_units"], 5)
		self.assertEqual(len(response.context["recent_sales"]), 1)
		self.assertEqual(len(response.context["low_stock"]), 1)
		self.assertContains(response, "Log Out")
		self.assertContains(response, 'action="/logout/"')
		self.assertContains(response, "Welcome to SENAMAT SUPERMARKET")
		self.assertContains(response, "supermarket management system that keeps track of customers")
		self.assertNotContains(response, "Record a sale")

	def test_about_page_shows_system_overview_and_contact_section(self):
		response = self.client.get("/about/")

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "about.html")
		self.assertContains(response, "Welcome to SENAMAT SUPERMARKET")
		self.assertContains(response, "keeps track of customers")
		self.assertContains(response, "Contact information")
		self.assertContains(response, "Phone:")
		self.assertContains(response, "Email:")
		self.assertContains(response, "Address:")
		self.assertContains(response, 'href="/about/"')
		self.assertContains(response, "dashboard.css?v=13")

	def test_root_url_shows_login_even_when_authenticated(self):
		response = self.client.get("/")

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "login.html")
		self.assertContains(response, "Log In")
		self.assertContains(response, "Create an account")

	def test_store_pages_require_login(self):
		self.client.logout()
		response = self.client.get("/category/")
		self.assertRedirects(response, "/login/?next=/category/")
		about_response = self.client.get("/about/")
		self.assertRedirects(about_response, "/login/?next=/about/")

	def test_signup_requires_a_valid_one_time_admin_invitation(self):
		self.client.logout()
		signup_page = self.client.get("/signup/")
		self.assertContains(signup_page, 'maxlength="5"')
		self.assertContains(signup_page, 'inputmode="numeric"')
		password = "S0mething-very-unrelated-938!"
		uninvited_response = self.client.post("/signup/", {
			"username": "new-cashier",
			"invitation_code": "not-a-valid-code",
			"password1": password,
			"password2": password,
		}, follow=True)

		self.assertEqual(uninvited_response.status_code, 200)
		self.assertFalse(get_user_model().objects.filter(username="new-cashier").exists())
		self.assertContains(uninvited_response, "Enter a valid value.")

		superuser = get_user_model().objects.create_superuser(
			username="invitation-admin",
			email="admin@example.com",
			password="Admin-password-123!",
		)
		invitation = SignupInvitation.objects.create(created_by=superuser)
		response = self.client.post("/signup/", {
			"username": "new-cashier",
			"invitation_code": invitation.code,
			"password1": password,
			"password2": password,
		}, follow=True)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.request["PATH_INFO"], "/home/")
		user = get_user_model().objects.get(username="new-cashier")
		self.assertIn("_auth_user_id", self.client.session)
		self.assertContains(response, "Your account has been created")
		invitation.refresh_from_db()
		self.assertEqual(invitation.used_by, user)
		self.assertIsNotNone(invitation.used_at)

		self.client.logout()
		reuse_response = self.client.post("/signup/", {
			"username": "another-cashier",
			"invitation_code": invitation.code,
			"password1": password,
			"password2": password,
		})
		self.assertEqual(reuse_response.status_code, 200)
		self.assertFalse(get_user_model().objects.filter(username="another-cashier").exists())
		self.assertContains(reuse_response, "invalid or has already been used")

	def test_authenticated_user_can_open_signup_form_without_redirect(self):
		cache.clear()
		signup_page = self.client.get("/signup/")

		self.assertEqual(signup_page.status_code, 200)
		self.assertTemplateUsed(signup_page, "signup.html")
		self.assertContains(signup_page, "Create an account")

		superuser = get_user_model().objects.create_superuser(
			username="signup-admin",
			email="admin@example.com",
			password="Admin-password-123!",
		)
		invitation = SignupInvitation.objects.create(created_by=superuser)
		password = "S0mething-very-unrelated-938!"
		response = self.client.post("/signup/", {
			"username": "invited-cashier",
			"invitation_code": invitation.code,
			"password1": password,
			"password2": password,
		}, follow=True)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.request["PATH_INFO"], "/home/")
		self.assertTrue(get_user_model().objects.filter(username="invited-cashier").exists())
		self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.user.pk))
		cache.clear()

	def test_only_superusers_can_create_signup_invitations_in_admin(self):
		superuser = get_user_model().objects.create_superuser(
			username="invitation-admin",
			email="admin@example.com",
			password="Admin-password-123!",
		)
		self.client.force_login(superuser)
		add_response = self.client.get("/admin/store/signupinvitation/add/")
		self.assertEqual(add_response.status_code, 200)
		save_response = self.client.post(
			"/admin/store/signupinvitation/add/",
			{"_save": "Save"},
		)
		self.assertEqual(save_response.status_code, 302)
		invitation = SignupInvitation.objects.get()
		self.assertEqual(invitation.created_by, superuser)
		self.assertRegex(invitation.code, r"^[0-9]{5}$")

		staff_user = get_user_model().objects.create_user(
			username="regular-staff",
			password="Staff-password-123!",
			is_staff=True,
		)
		self.client.force_login(staff_user)
		staff_response = self.client.get("/admin/store/signupinvitation/add/")
		self.assertEqual(staff_response.status_code, 403)

	def test_signup_limits_invalid_invitation_code_attempts(self):
		cache.clear()
		self.client.logout()
		post_data = {
			"username": "unauthorized-cashier",
			"invitation_code": "00000",
			"password1": "S0mething-very-unrelated-938!",
			"password2": "S0mething-very-unrelated-938!",
		}

		for _ in range(5):
			response = self.client.post("/signup/", post_data)
			self.assertEqual(response.status_code, 200)

		blocked_response = self.client.post("/signup/", post_data)
		self.assertContains(blocked_response, "Too many failed code attempts")
		self.assertFalse(get_user_model().objects.filter(username="unauthorized-cashier").exists())
		cache.clear()

	def test_logout_ends_authenticated_session(self):
		response = self.client.post("/logout/", follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.request["PATH_INFO"], "/login/")
		self.assertNotIn("_auth_user_id", self.client.session)

	def test_valid_posts_create_records(self):
		submissions = (
			("/category/", {"category_name": "Fresh Food"}, Category),
			("/customer/", {
				"customer_name": "Sam", "contact": "0712345678", "gender": "Other",
				"address": "Kampala",
			}, Customer),
			("/purchase-item/", {
				"purchase": self.purchase.pk, "product": self.product.pk, "store": self.store.pk,
				"quantity": 2, "unit_price": "2.50",
			}, PurchaseItem),
			("/purchases/", {"supplier_name": "Another Supplier"}, Purchases),
			("/sales/", {"customer": self.customer.pk}, Sales),
			("/sales-item/", {
				"sale": self.sale.pk, "product": self.product.pk, "store": self.store.pk,
				"quantity": 1, "unit_price": "2.50",
			}, SalesItem),
			("/store/", {"store_name": "Entebbe"}, Store),
		)

		for path, data, model in submissions:
			with self.subTest(path=path):
				initial_count = model.objects.count()
				response = self.client.post(path, data, follow=True)
				self.assertEqual(response.status_code, 200)
				self.assertEqual(model.objects.count(), initial_count + 1)
				self.assertContains(response, "saved successfully")
				self.assertTrue(response.redirect_chain[0][0].endswith("?saved=1"))
				self.assertFalse(response.context["show_form"])
				self.assertTrue(response.context["show_records"])
				self.assertContains(response, 'aria-hidden="true" hidden')
				self.assertContains(response, str(model.objects.order_by("-pk").first().pk))

				view_response = self.client.get(path, {"view": "1"})
				self.assertTrue(view_response.context["show_records"])
				self.assertContains(view_response, str(model.objects.order_by("-pk").first().pk))

	def test_receipt_reads_items_added_after_sale_creation(self):
		sale_response = self.client.post("/sales/", {"customer": self.customer.pk})
		self.assertRedirects(sale_response, "/sales/?saved=1", fetch_redirect_response=False)
		sale = Sales.objects.latest("pk")
		initial_stock = Inventory.objects.get(product=self.product, store=self.store).quantity

		item_response = self.client.post("/sales-item/", {
			"sale": sale.pk,
			"product": self.product.pk,
			"store": self.store.pk,
			"quantity": 2,
			"unit_price": "2.50",
		})
		self.assertRedirects(item_response, "/sales-item/?saved=1", fetch_redirect_response=False)
		sale.refresh_from_db()
		self.assertEqual(sale.total_amount, Decimal("5.00"))
		self.assertEqual(sale.items.count(), 1)
		self.assertEqual(Inventory.objects.get(product=self.product, store=self.store).quantity, initial_stock - 2)

		response = self.client.get("/sales/")
		self.assertContains(response, f'href="/sales/{sale.pk}/receipt/"')
		self.assertContains(response, "Add New Sale")
		self.assertNotContains(response, "Add item")

		receipt_response = self.client.get(f"/sales/{sale.pk}/receipt/")
		self.assertEqual(receipt_response.status_code, 200)
		self.assertContains(receipt_response, "SENAMAT SUPERMARKET")
		self.assertContains(receipt_response, "Ada")
		self.assertContains(receipt_response, "Tea")
		self.assertContains(receipt_response, "5.00 shs")
		self.assertContains(receipt_response, "Not entered")
		self.assertContains(receipt_response, "Enter amount paid")
		self.assertContains(receipt_response, "Print Receipt")
		self.assertContains(receipt_response, "disabled")

		payment_response = self.client.post(f"/sales/{sale.pk}/receipt/", {
			"amount_paid": "6.00",
			"save_payment": "1",
		})
		self.assertRedirects(payment_response, f"/sales/{sale.pk}/receipt/", fetch_redirect_response=False)
		sale.refresh_from_db()
		self.assertEqual(sale.amount_paid, Decimal("6.00"))
		updated_receipt = self.client.get(f"/sales/{sale.pk}/receipt/")
		self.assertContains(updated_receipt, "6.00 shs")
		self.assertContains(updated_receipt, "1.00 shs")
		self.assertNotContains(updated_receipt, "disabled")

	def test_receipt_rejects_zero_and_underpayment_accepts_exact_payment(self):
		sale = Sales.objects.create(customer=self.customer)
		SalesItem.objects.create(
			sale=sale, product=self.product, store=self.store,
			quantity=1, unit_price="2.50",
		)

		for amount in ("0.00", "2.49"):
			with self.subTest(amount=amount):
				response = self.client.post(f"/sales/{sale.pk}/receipt/", {
					"amount_paid": amount,
					"save_payment": "1",
				})
				self.assertEqual(response.status_code, 200)
				self.assertTrue(response.context["payment_form"].errors)
				sale.refresh_from_db()
				self.assertEqual(sale.amount_paid, Decimal("0.00"))

		exact_payment = self.client.post(f"/sales/{sale.pk}/receipt/", {
			"amount_paid": "2.50",
			"save_payment": "1",
		})
		self.assertRedirects(exact_payment, f"/sales/{sale.pk}/receipt/", fetch_redirect_response=False)
		sale.refresh_from_db()
		self.assertEqual(sale.amount_paid, Decimal("2.50"))
		self.assertContains(self.client.get(f"/sales/{sale.pk}/receipt/"), "0.00 shs")

	def test_print_receipt_saves_pdf_under_static_receipts(self):
		sale = Sales.objects.create(customer=self.customer, amount_paid="2.50")
		SalesItem.objects.create(
			sale=sale, product=self.product, store=self.store,
			quantity=1, unit_price="2.50",
		)

		with TemporaryDirectory() as temporary_directory:
			logo_directory = Path(temporary_directory) / "store" / "static" / "assets" / "dashboard" / "images"
			logo_directory.mkdir(parents=True)
			shutil.copyfile(
				Path(__file__).parent / "static" / "assets" / "dashboard" / "images" / "logo1.png",
				logo_directory / "logo1.png",
			)
			with override_settings(BASE_DIR=Path(temporary_directory)):
				response = self.client.post(f"/sales/{sale.pk}/receipt/", {"print_receipt": "1"})
				pdf_path = Path(temporary_directory) / "store" / "static" / "receipts" / f"receipt-{sale.pk}.pdf"
				self.assertEqual(response.status_code, 200)
				self.assertEqual(response["Content-Type"], "application/pdf")
				self.assertTrue(pdf_path.is_file())
				self.assertTrue(b"%PDF" in b"".join(response.streaming_content))

	def test_purchase_item_requires_an_existing_product(self):
		response = self.client.post("/purchase-item/", {
			"purchase": self.purchase.pk,
			"product": "Coffee",
			"store": self.other_store.pk,
			"quantity": 2,
			"unit_price": "2.25",
		})

		self.assertEqual(response.status_code, 200)
		self.assertFalse(Product.objects.filter(item="Coffee").exists())
		self.assertEqual(PurchaseItem.objects.count(), 1)

	def test_purchase_item_product_is_a_dropdown_of_existing_products(self):
		response = self.client.get("/purchase-item/")

		self.assertContains(response, 'id="id_product"')
		self.assertContains(response, '<select name="product"', html=False)
		self.assertContains(response, f'<option value="{self.product.pk}">Tea</option>', html=False)
		self.assertContains(response, f'<option value="{self.other_product.pk}">Soap</option>', html=False)

	def test_item_records_show_supplier_and_sale_foreign_key_without_prefix(self):
		purchase_response = self.client.get("/purchase-item/")
		sales_response = self.client.get("/sales-item/")

		self.assertContains(purchase_response, "<td>Supplier</td>", html=False)
		self.assertContains(sales_response, "<td>Ada</td>", html=False)
		self.assertContains(
			purchase_response,
			f'<option value="{self.purchase.pk}">Supplier ({self.purchase.pk})</option>',
			html=False,
		)
		self.assertContains(
			sales_response,
			f'<option value="{self.sale.pk}">Ada ({self.sale.pk})</option>',
			html=False,
		)
		self.assertNotContains(purchase_response, f"Purchase #{self.purchase.pk}")
		self.assertNotContains(sales_response, f"Sale #{self.sale.pk}")

	def test_product_form_uses_a_text_item_field_and_creates_products(self):
		form_response = self.client.get("/product/")
		self.assertContains(form_response, 'id="id_item"')
		self.assertContains(form_response, '<input type="text" name="item"', html=False)
		self.assertNotContains(form_response, '<select name="item"', html=False)

		response = self.client.post("/product/", {
			"item": "Coffee",
			"unit_price": "3.50",
			"brand": "Clean",
			"color": "White",
			"model": "S2",
			"category": self.category.pk,
		}, follow=True)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Product.objects.count(), 3)
		product = Product.objects.get(item="Coffee")
		self.assertEqual(product.unit_price, Decimal("3.50"))
		self.assertEqual(product.brand, "Clean")
		self.assertEqual(product.category, self.category)
		self.assertContains(response, "Product saved successfully")

	def test_sales_item_product_dropdown_excludes_incomplete_products(self):
		Product.objects.create(item="Incomplete")
		response = self.client.get("/sales-item/")

		self.assertContains(response, "Tea")
		self.assertNotContains(response, "Incomplete")

	def test_invalid_post_is_not_saved(self):
		response = self.client.post("/customer/", {"customer_name": "", "contact": ""})

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Customer.objects.count(), 1)
		self.assertContains(response, "Customer name: This field is required")

	def test_database_save_failure_shows_error_and_does_not_claim_success(self):
		product_data = {
			"item": str(self.product.pk), "unit_price": "4.50", "brand": "Fresh",
			"color": "Brown", "model": "C1", "category": self.category.pk,
		}
		with self.assertLogs("store.views", level="ERROR"):
			with patch("store.views.ProductForm.save", side_effect=DatabaseError("write failed")):
				response = self.client.post("/product/", product_data)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "database rejected the change")
		self.assertNotContains(response, "Product saved successfully")
		self.assertEqual(Product.objects.count(), 2)

	def test_edit_and_delete_records(self):
		response = self.client.post("/customer/", {
			"edit_pk": self.customer.pk,
			"customer_name": "Ada Updated",
			"contact": "0700000001",
			"gender": "Female",
			"address": "Kampala",
		}, follow=True)
		self.assertEqual(response.status_code, 200)
		self.customer.refresh_from_db()
		self.assertEqual(self.customer.customer_name, "Ada Updated")
		self.assertContains(response, "updated successfully")

		store_to_delete = Store.objects.create(store_name="Temporary")
		response = self.client.post("/store/", {"delete_pk": store_to_delete.pk}, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertFalse(Store.objects.filter(pk=store_to_delete.pk).exists())
		self.assertEqual(response.request["PATH_INFO"], "/store/")
		self.assertIn("deleted=1", response.request["QUERY_STRING"])
		self.assertContains(response, "Store deleted successfully")

	def test_login_authenticates_and_redirects_home(self):
		self.client.logout()
		response = self.client.post("/login/", {
			"username": "cashier",
			"password": "test-password-123",
		}, follow=True)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.request["PATH_INFO"], "/home/")
		self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.user.pk))

	def test_category_duplicates_are_rejected_case_insensitively(self):
		response = self.client.post("/category/", {"category_name": "electronics"})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Category.objects.count(), 1)
		self.assertContains(response, "This category already exists")

	def test_customer_without_sales_has_zero_spending(self):
		customer = Customer.objects.create(customer_name="No Sales Yet")
		response = self.client.get("/customer/", {"view": "1"})
		listed_customer = response.context["records"].get(pk=customer.pk)
		self.assertEqual(listed_customer.amount_spent, 0)
		self.assertContains(response, "0.00 shs")

	def test_purchase_sales_totals_and_inventory_follow_line_items(self):
		self.purchase.refresh_from_db()
		self.sale.refresh_from_db()
		self.assertEqual(self.purchase.total_amount, 5)
		self.assertEqual(self.sale.total_amount, 2.5)
		self.assertEqual(Sales.objects.filter(customer=self.customer).aggregate(total=Sum("total_amount"))["total"], 2.5)
		self.assertEqual(Inventory.objects.get(product=self.product, store=self.store).quantity, 5)

		purchase_item = PurchaseItem.objects.create(
			purchase=self.purchase, product=self.product, store=self.store,
			quantity=3, unit_price="4.00",
		)
		self.purchase.refresh_from_db()
		self.assertEqual(self.purchase.total_amount, 17)
		self.assertEqual(Inventory.objects.get(product=self.product, store=self.store).quantity, 8)

		sales_item = SalesItem.objects.create(
			sale=self.sale, product=self.product, store=self.store,
			quantity=2, unit_price="3.00",
		)
		self.sale.refresh_from_db()
		self.assertEqual(self.sale.total_amount, 8.5)
		self.assertEqual(Sales.objects.filter(customer=self.customer).aggregate(total=Sum("total_amount"))["total"], 8.5)
		self.assertEqual(Inventory.objects.get(product=self.product, store=self.store).quantity, 6)

		sales_item.delete()
		purchase_item.delete()
		self.sale.refresh_from_db()
		self.purchase.refresh_from_db()
		self.assertEqual(self.sale.total_amount, 2.5)
		self.assertEqual(self.purchase.total_amount, 5)
		self.assertEqual(Inventory.objects.get(product=self.product, store=self.store).quantity, 5)

	def test_sales_items_cannot_exceed_store_stock(self):
		response = self.client.post("/sales-item/", {
			"sale": self.sale.pk,
			"product": self.product.pk,
			"store": self.other_store.pk,
			"quantity": 1,
			"unit_price": "2.50",
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(SalesItem.objects.count(), 1)
		self.assertContains(response, "does not have enough stock")
