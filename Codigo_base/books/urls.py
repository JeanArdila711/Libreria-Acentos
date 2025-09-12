# books/urls.py

from django.urls import path
from .views import HomePageView, AboutPageView, BookListView, BookSearchView, statistics_view, promociones_view, filter_options_ajax
from .ia_api import ia_book_synopsis

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('books/', BookListView.as_view(), name='book_list'),
    path('books/search/', BookSearchView.as_view(), name='book_search'),
    path('books/statistics/', statistics_view, name='book_statistics'),
    path('promociones/', promociones_view, name='promociones'),
    path('books/filter-options/', filter_options_ajax, name='books_filter_options'),
    path('books/ia-synopsis/', ia_book_synopsis, name='books_ia_synopsis'),
    
]