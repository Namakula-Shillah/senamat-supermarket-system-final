from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('', LoginView.as_view(
        template_name='login.html',
        next_page='home',
        redirect_authenticated_user=False,
    ), name='root'),
    path('login/', LoginView.as_view(template_name='login.html', next_page='home'), name='login'),
    path('signup/', views.signup, name='signup'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('category/', views.add_category_view, name='category'),
    path('customer/', views.add_customer_view, name='customer'),
    path('inventory/', views.update_inventory_view, name='inventory'),
    path('product/', views.add_product_view, name='product'),
    path('purchase-item/', views.add_purchase_item_view, name='purchase_item'),
    path('purchases/', views.add_purchase_view, name='purchases'),
    path('sales-item/', views.add_sales_item_view, name='sales_item'),
    path('sales/', views.add_sales_view, name='sales'),
    path('sales/<int:pk>/receipt/', views.sale_receipt, name='sale_receipt'),
    path('store/', views.add_store_view, name='store'),
]