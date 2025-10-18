# books/urls.py

from django.urls import path
from .views import HomePageView, AboutPageView, BookListView, BookSearchView, statistics_view, promociones_view, filter_options_ajax
from .ia_api import ia_book_synopsis
from .views import (HomePageView, AboutPageView, BookListView, BookSearchView, statistics_view,promociones_view,recommend_book,filter_options_ajax,book_detail, add_to_cart,buy_now,cart_view)
from . import views

urlpatterns = [
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
    path('buy/<int:book_id>/', views.buy_now, name='buy_now'),
    path('cart/add/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/update/<int:book_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:book_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
]