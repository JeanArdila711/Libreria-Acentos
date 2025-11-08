from django.urls import path
from .views import (
    HomePageView, AboutPageView, BookListView, BookSearchView,
    statistics_view, promociones_view, recommend_book, filter_options_ajax,
    book_detail, add_to_cart, buy_now, cart_view,
    UserProfileView, edit_profile, my_orders, order_detail,
    my_favorites, toggle_favorite, user_statistics, user_settings,
    create_order_from_cart, Top100BooksView,
    checkout_view, payment_method_view, process_payment_view, payment_success_view
)
from .ia_api import ia_book_synopsis
from . import views

urlpatterns = [
    # Home y básicas
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('catalogo/', BookListView.as_view(), name='book_list'),
    path('books/search/', BookSearchView.as_view(), name='book_search'),
    path('books/statistics/', statistics_view, name='book_statistics'),
    path('promociones/', promociones_view, name='promociones'),
    path('books/filter-options/', filter_options_ajax, name='books_filter_options'),
    path('books/ia-synopsis/', ia_book_synopsis, name='books_ia_synopsis'),
    path('recommend/', views.recommend_book, name='recommend_book'),
    path('filter-options/', filter_options_ajax, name='filter_options_ajax'),
    path('book/<int:book_id>/', book_detail, name='book_detail'),
    path('top-100/', Top100BooksView.as_view(), name='top_100'),
    
    # Carrito
    path('buy/<int:book_id>/', views.buy_now, name='buy_now'),
    path('cart/add/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/update/<int:book_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:book_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/checkout/', create_order_from_cart, name='create_order'),

    # Proceso de pago
    path('checkout/', checkout_view, name='checkout'),
    path('checkout/payment-method/', payment_method_view, name='payment_method'),
    path('checkout/process/<str:payment_method>/', process_payment_view, name='process_payment'),
    path('checkout/success/<int:order_id>/', payment_success_view, name='payment_success'),
    
    # 🆕 PERFIL DE USUARIO
    path('perfil/', UserProfileView.as_view(), name='user_profile'),
    path('perfil/editar/', edit_profile, name='edit_profile'),
    
    # 🆕 PEDIDOS
    path('mis-pedidos/', my_orders, name='my_orders'),
    path('pedido/<int:order_id>/', order_detail, name='order_detail'),
    
    # 🆕 FAVORITOS
    path('favoritos/', my_favorites, name='my_favorites'),
    path('favoritos/toggle/<int:book_id>/', toggle_favorite, name='toggle_favorite'),
    
    # 🆕 ESTADÍSTICAS
    path('estadisticas/', user_statistics, name='user_statistics'),
    
    # 🆕 CONFIGURACIÓN
    path('configuracion/', user_settings, name='user_settings'),
    # Reseñas
    path('book/<int:book_id>/review/add/', views.add_review, name='add_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/helpful/', views.mark_review_helpful, name='mark_review_helpful'),
    path('recomendaciones/', views.personalized_recommendations_view, name='personalized_recommendations'),


]
