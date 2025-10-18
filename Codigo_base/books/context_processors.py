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

def cart_counter(request):
    cart = request.session.get('cart', {})
    try:
        return {"cart_count": sum(int(q) for q in cart.values())}
    except Exception:
        return {"cart_count": 0}
