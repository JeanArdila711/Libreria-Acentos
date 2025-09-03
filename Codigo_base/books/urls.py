# books/urls.py

from django.urls import path
from .views import HomePageView, AboutPageView, BookListView, BookSearchView, statistics_view,promociones_view

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('books/', BookListView.as_view(), name='book_list'),
    path('books/search/', BookSearchView.as_view(), name='book_search'),
    path('books/statistics/', statistics_view, name='book_statistics'),
    path('promociones/', promociones_view, name='promociones'),
    
]