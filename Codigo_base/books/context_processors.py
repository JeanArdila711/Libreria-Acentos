from .models import Book


def common_context(request):
    genres = Book.objects.values_list('genre', flat=True).distinct().order_by('genre')
    authors = Book.objects.values_list('authors', flat=True).distinct().order_by('authors')
    featured_books = Book.objects.all()[:12]

    return {
        'app_name': "Biblioteca Acentos",
        'all_genres': genres,
        'all_authors': authors,
        'featured_books': featured_books,
    }
