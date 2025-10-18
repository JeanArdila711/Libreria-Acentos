from .models import Book
from django.urls import reverse

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


def back_button_context(request):
    """Muestra el botón de volver atrás en todas las páginas menos el home."""
    current_path = request.path.rstrip('/')
    home_path = reverse("home").rstrip('/')
    return {
        "show_back_button": current_path != home_path and current_path != ""
    }
