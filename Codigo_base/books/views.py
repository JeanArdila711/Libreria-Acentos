from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView
from django.db.models import Q, Count
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
import numpy as np
import os
import io
import base64
import urllib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from .models import Book

# -------------------------------------------------------
# 1️⃣ FILTROS AJAX
# -------------------------------------------------------
@require_GET
def filter_options_ajax(request):
    genres = request.GET.getlist('genre')
    authors = request.GET.getlist('author')
    qs = Book.objects.all()

    if genres:
        qs = qs.filter(genre__in=genres)
    if authors:
        qs = qs.filter(
            authors__regex=r'(' + '|'.join([a.replace('.', '\.') for a in authors]) + ')'
        )

    valid_genres = list(qs.values_list('genre', flat=True)
                        .exclude(genre='')
                        .distinct()
                        .order_by('genre'))

    autores_raw = qs.values_list('authors', flat=True).exclude(authors='').distinct()
    autores_set = set()
    for autores in autores_raw:
        for autor in autores.split('/'):
            autores_set.add(autor.strip())
    valid_authors = sorted(autores_set)

    return JsonResponse({'genres': valid_genres, 'authors': valid_authors})

# -------------------------------------------------------
# 2️⃣ HOME, LISTA, DETALLE Y ESTADÍSTICAS
# -------------------------------------------------------
class HomePageView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from random import sample
        books = list(Book.objects.all())
        ctx['featured_books'] = sample(books, min(len(books), 6))
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
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = Book.objects.values_list('genre', flat=True).exclude(genre='').distinct().order_by('genre')

        autores_raw = Book.objects.values_list('authors', flat=True).exclude(authors='').distinct()
        autores_set = set()
        for autores in autores_raw:
            for autor in autores.split('/'):
                autores_set.add(autor.strip())
        context['authors'] = sorted(autores_set)

        request = self.request
        context['selected_genres'] = request.GET.getlist('genre')
        context['selected_authors'] = request.GET.getlist('author')
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(authors__icontains=search) |
                Q(genre__icontains=search)
            )

        genres = self.request.GET.getlist('genre') or self.request.GET.get('genre')
        if genres:
            if isinstance(genres, str):
                genres = [genres]
            qs = qs.filter(genre__in=genres)

        authors = self.request.GET.getlist('author') or self.request.GET.get('author')
        if authors:
            if isinstance(authors, str):
                authors = [authors]
            qs = qs.filter(authors__in=authors)

        language = self.request.GET.get('language_code')
        if language:
            qs = qs.filter(language_code=language)

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
                Q(authors__icontains=query) |
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
    plt.figure(figsize=(8, 4))
    years = sorted(book_counts_by_year.keys())
    values = [book_counts_by_year[y] for y in years]
    plt.bar(years, values, color="#20bfa9")
    plt.title('Libros por año')
    plt.xticks(rotation=90)
    plt.tight_layout()
    buffer1 = io.BytesIO()
    plt.savefig(buffer1, format='png')
    graphic_year = base64.b64encode(buffer1.getvalue()).decode('utf-8')
    buffer1.close()
    plt.close()

    # Gráfica por género
    plt.figure(figsize=(8, 4))
    genres = sorted(book_counts_by_genre.keys())
    values = [book_counts_by_genre[g] for g in genres]
    plt.bar(genres, values, color="#178f7a")
    plt.title('Libros por género')
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer2 = io.BytesIO()
    plt.savefig(buffer2, format='png')
    graphic_genre = base64.b64encode(buffer2.getvalue()).decode('utf-8')
    buffer2.close()
    plt.close()

    return render(request, 'statistics.html', {
        'graphic_year': graphic_year,
        'graphic_genre': graphic_genre
    })


def promociones_view(request):
    return render(request, "books/promociones.html")


def book_detail(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    return render(request, "books/book_detail.html", {"book": book})

# -------------------------------------------------------
# 3️⃣ RECOMENDADOR CON OPENAI
# -------------------------------------------------------
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'openAI.env'))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

@csrf_exempt
def recommend_book(request):
    if request.method == "POST":
        prompt = request.POST.get("prompt", "").strip()
        if not prompt:
            return render(request, "books/recommend.html", {
                "error": "Por favor escribe una descripción o preferencia."
            })

        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[prompt]
            )
            prompt_emb = np.array(response.data[0].embedding, dtype=np.float32)

            books_with_similarity = []
            for book in Book.objects.all():
                try:
                    book_emb = np.frombuffer(book.emb, dtype=np.float32)
                    similarity = cosine_similarity(prompt_emb, book_emb)
                    books_with_similarity.append((book, similarity))
                except Exception:
                    continue

            books_with_similarity.sort(key=lambda x: x[1], reverse=True)
            top_books = books_with_similarity[:3]

            context = {
                "prompt": prompt,
                "recommendations": [
                    {"book": b, "similarity": round(float(s), 4)} for b, s in top_books
                ]
            }
            return render(request, "books/recommend.html", context)

        except Exception as e:
            return render(request, "books/recommend.html", {
                "error": f"Ocurrió un error: {e}"
            })

    return render(request, "books/recommend.html")


# -------------------------------------------------------
# 4️⃣ CARRITO DE COMPRAS
# -------------------------------------------------------

def _get_qty(value):
    """Devuelve cantidad válida sin importar el formato viejo o nuevo."""
    if isinstance(value, dict):
        return int(value.get("quantity", 1))
    return int(value)

def add_to_cart(request, book_id):
    """Agrega un libro al carrito o incrementa si ya existe."""
    cart = request.session.get('cart', {})
    # Si detecta formato viejo, limpia
    if any(isinstance(v, dict) for v in cart.values()):
        cart = {}

    book = get_object_or_404(Book, pk=book_id)
    key = str(book_id)

    current = cart.get(key, 0)
    try:
        current = _get_qty(current)
    except Exception:
        current = 0

    cart[key] = current + 1
    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, f"Agregado al carrito: {book.title}")
    return redirect('cart_view')

def update_cart(request, book_id, action):
    """Actualiza cantidad (+/-) desde el carrito."""
    if request.method != 'POST':
        return redirect('cart_view')

    cart = request.session.get('cart', {})
    key = str(book_id)

    if key in cart:
        try:
            qty = _get_qty(cart[key])
        except Exception:
            qty = 1

        if action == "increase":
            qty += 1
        elif action == "decrease":
            qty = max(1, qty - 1)

        cart[key] = qty
        request.session['cart'] = cart
        request.session.modified = True

    return redirect('cart_view')

def remove_from_cart(request, book_id):
    """Elimina un libro del carrito."""
    cart = request.session.get('cart', {})
    key = str(book_id)
    if key in cart:
        del cart[key]
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, "Libro eliminado del carrito 🗑️")
    return redirect('cart_view')

def cart_view(request):
    """Muestra el carrito con todos los libros agregados."""
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0.0

    for book_id_str, raw_qty in cart.items():
        try:
            qty = _get_qty(raw_qty)
        except Exception:
            qty = 1

        try:
            book_id = int(book_id_str)
            book = Book.objects.get(pk=book_id)
        except (ValueError, Book.DoesNotExist):
            continue

        try:
            price = float(book.price or 0)
        except Exception:
            price = 0.0

        subtotal = round(price * qty, 2)
        total_price += subtotal
        cart_items.append({
            "book": book,
            "quantity": qty,
            "subtotal": subtotal,
        })

    return render(request, "books/cart.html", {
        "cart_items": cart_items,
        "total_price": round(total_price, 2),
    })

def clear_cart(request):
    """Vacía completamente el carrito."""
    request.session['cart'] = {}
    request.session.modified = True
    messages.info(request, "Carrito vaciado 🧹")
    return redirect('cart_view')

def buy_now(request, book_id):
    """Agrega el libro al carrito y redirige a la vista del carrito."""
    book = get_object_or_404(Book, pk=book_id)
    cart = request.session.get('cart', {})
    key = str(book_id)
    cart[key] = cart.get(key, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart_view')
