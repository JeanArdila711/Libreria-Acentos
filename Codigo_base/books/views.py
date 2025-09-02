
from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from .models import Book
from django.db.models import Q
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import urllib, base64


class HomePageView(TemplateView):
    template_name = "home.html"

class AboutPageView(TemplateView):
    template_name = "about.html"

class BookListView(ListView):
    model = Book
    template_name = "book_list.html"
    context_object_name = "books"
    paginate_by = 6

    def get_queryset(self):
        return super().get_queryset()

class BookSearchView(ListView):
    model = Book
    template_name = "book_search_results.html"
    context_object_name = "books"
    paginate_by = 6

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Book.objects.filter(
                Q(title__icontains=query) |
                Q(author__icontains=query) |
                Q(genre__icontains=query)
            ).distinct()
        return Book.objects.none()

def statistics_view(request):
    all_books = Book.objects.all()
    # Libros por año
    book_counts_by_year = {}
    for book in all_books:
        year = str(book.publication_year) if book.publication_year else "Sin año"
        book_counts_by_year[year] = book_counts_by_year.get(year, 0) + 1

    # Libros por género
    book_counts_by_genre = {}
    for book in all_books:
        genre = book.genre if book.genre else "Sin género"
        book_counts_by_genre[genre] = book_counts_by_genre.get(genre, 0) + 1

    # Gráfica por año
    plt.figure(figsize=(8,4))
    years = sorted(book_counts_by_year.keys())
    values = [book_counts_by_year[year] for year in years]
    plt.bar(years, values, width=0.5, align='center', color="#20bfa9")
    plt.title('Libros por año')
    plt.xlabel('Año')
    plt.ylabel('Cantidad de libros')
    plt.xticks(rotation=90)
    plt.tight_layout()
    buffer1 = io.BytesIO()
    plt.savefig(buffer1, format='png')
    buffer1.seek(0)
    graphic_year = base64.b64encode(buffer1.getvalue()).decode('utf-8')
    buffer1.close()
    plt.close()

    # Gráfica por género
    plt.figure(figsize=(8,4))
    genres = sorted(book_counts_by_genre.keys())
    values = [book_counts_by_genre[genre] for genre in genres]
    plt.bar(genres, values, width=0.5, align='center', color="#178f7a")
    plt.title('Libros por género')
    plt.xlabel('Género')
    plt.ylabel('Cantidad de libros')
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer2 = io.BytesIO()
    plt.savefig(buffer2, format='png')
    buffer2.seek(0)
    graphic_genre = base64.b64encode(buffer2.getvalue()).decode('utf-8')
    buffer2.close()
    plt.close()

    return render(request, 'statistics.html', {
        'graphic_year': graphic_year,
        'graphic_genre': graphic_genre
    })