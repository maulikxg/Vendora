from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('product/<int:product_id>', views.detail, name='detail'),
    path('success', views.payment_success_view, name='success'),
    path('failed', views.payment_failed_view, name='failed'),
    path('api/checkout-session/<int:product_id>', views.create_checkout_session, name='api_checkout_session'),
    path('createproduct',views.create_product, name='createproduct'),
    path('product/<int:product_id>/edit', views.product_edit, name='editproduct'),
    path('product/<int:product_id>/delete', views.product_delete, name='delete'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('register', views.register, name='register'),
    path('login', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout', auth_views.LogoutView.as_view(template_name='app/logout.html', http_method_names=['get', 'post']), name='logout'),
    path('invalid', views.invalid, name='invalid'),
    path('purchases', views.my_purchases, name='purchases'),
    path('sales', views.sales, name='sales'),
    
]