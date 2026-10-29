from django.urls import path
from . import views

app_name = 'cargo_14'

urlpatterns = [
    path('', views.home, name='home'),
    path('news/', views.news_view, name='news'),
    path('set-language/', views.set_language_view, name='set_language'),



    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('my-products/', views.my_products_view, name='my_products'),
    path('product/add/', views.add_product_view, name='add_product'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/delete/<int:pk>/', views.delete_product_view, name='delete_product'),
    path('favorite/toggle/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_list, name='favorites_list'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('apply-promocode/', views.apply_promocode_view, name='apply_promocode'),
    path('support/', views.support_view, name='support'),
    path('payment-methods/', views.manage_payment_methods_view, name='manage_payment_methods'),
    path('thank-you/', views.thank_you_view, name='thank_you'),
    path('product/<int:pk>/edit-main-image/', views.edit_product_main_image_view, name='edit_product_main_image'),
    path('presentation/', views.presentation_view, name='presentation'),
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant'),
]
