
from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from .models import Book
from django.db.models import Q
from django.db.models import Count
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import urllib, base64


class HomePageView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Top 10 géneros por cantidad de libros
        genres = (
            Book.objects.values('genre')
            .exclude(genre="")
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        ctx['top_genres'] = genres
        return ctx

class AboutPageView(TemplateView):
    template_name = "about.html"

class BookListView(ListView):
    model = Book
    template_name = "book_list.html"
    context_object_name = "books"
    paginate_by = 6

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtro por géneros (múltiples)
        genres = self.request.GET.getlist('genre') or self.request.GET.get('genre')
        if genres:
            if isinstance(genres, str):
                genres = [genres]
            qs = qs.filter(genre__in=genres)

        # Filtro por autores (múltiples)
        authors = self.request.GET.getlist('author') or self.request.GET.get('author')
        if authors:
            if isinstance(authors, str):
                authors = [authors]
            qs = qs.filter(author__in=authors)

        # Orden básico por título
        return qs.order_by('title')

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
def promociones_view(request):
    return render(request, "promociones.html")
