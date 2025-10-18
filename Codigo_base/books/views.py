from django.http import JsonResponse
# Endpoint AJAX para filtros cruzados
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
@require_GET
def filter_options_ajax(request):
    genres = request.GET.getlist('genre')
    authors = request.GET.getlist('author')
    qs = Book.objects.all()
    if genres:
        qs = qs.filter(genre__in=genres)
    if authors:
        qs = qs.filter(
            # autores separados por /
            authors__regex=r'(' + '|'.join([a.replace('.', '\.') for a in authors]) + ')'
        )
    # Géneros válidos según autores seleccionados
    valid_genres = list(qs.values_list('genre', flat=True).exclude(genre='').distinct().order_by('genre'))
    # Autores válidos según géneros seleccionados
    autores_raw = qs.values_list('authors', flat=True).exclude(authors='').distinct()
    autores_set = set()
    for autores in autores_raw:
        for autor in autores.split('/'):
            autores_set.add(autor.strip())
    valid_authors = sorted(autores_set)
    return JsonResponse({'genres': valid_genres, 'authors': valid_authors})

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
        from random import sample
        books = list(Book.objects.all())
        ctx['featured_books'] = sample(books, min(len(books), 6))  # 6 libros aleatorios o menos
        # Top 10 géneros por cantidad de libros (si lo querés seguir mostrando en el home)
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
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Lista de géneros únicos ordenados
        context['genres'] = Book.objects.values_list('genre', flat=True).exclude(genre='').distinct().order_by('genre')
        # Lista de autores únicos ordenados (puede haber autores múltiples por libro, separados por /)
        autores_raw = Book.objects.values_list('authors', flat=True).exclude(authors='').distinct()
        autores_set = set()
        for autores in autores_raw:
            for autor in autores.split('/'):
                autores_set.add(autor.strip())
        context['authors'] = sorted(autores_set)
        # Pasar géneros y autores seleccionados para la plantilla
        request = self.request
        context['selected_genres'] = request.GET.getlist('genre')
        context['selected_authors'] = request.GET.getlist('author')
        return context
    model = Book
    template_name = "book_list.html"
    context_object_name = "books"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        # Búsqueda general por título, autor o género
        search = self.request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(authors__icontains=search) |
                Q(genre__icontains=search)
            )

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
            qs = qs.filter(authors__in=authors)

        # Filtro por idioma (opcional)
        language = self.request.GET.get('language_code')
        if language:
            qs = qs.filter(language_code=language)

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
    return render(request, "books/promociones.html")

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from openai import OpenAI
import numpy as np
import os
from dotenv import load_dotenv
from .models import Book

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
            # 1️⃣ Generar el embedding del prompt
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[prompt]
            )
            prompt_emb = np.array(response.data[0].embedding, dtype=np.float32)

            # 2️⃣ Calcular similitud con todos los libros
            books_with_similarity = []
            for book in Book.objects.all():
                try:
                    book_emb = np.frombuffer(book.emb, dtype=np.float32)
                    similarity = cosine_similarity(prompt_emb, book_emb)
                    books_with_similarity.append((book, similarity))
                except Exception:
                    continue  # por si algún registro tiene embedding dañado

            # 3️⃣ Ordenar por similitud descendente y tomar los 3 primeros
            books_with_similarity.sort(key=lambda x: x[1], reverse=True)
            top_books = books_with_similarity[:3]

            # 4️⃣ Preparar datos para la plantilla
            context = {
                "prompt": prompt,
                "recommendations": [
                    {"book": b, "similarity": round(float(s), 4)} for b, s in top_books
                ]
            }

            return render(request, "books/recommend.html", context)

        except Exception as e:
            return render(request, "books/recommend.html", {
                "error": f"Ocurrió un error al generar las recomendaciones: {e}"
            })

    # Si no es POST, mostrar el formulario vacío
    return render(request, "books/recommend.html")


from django.shortcuts import get_object_or_404

def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, "books/book_detail.html", {"book": book})

from django.contrib import messages
from django.shortcuts import redirect

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Book

# ---------- Helpers ----------
def _get_cart(request):
    """Obtiene el carrito desde la sesión como dict {str(book_id): qty}."""
    return request.session.get('cart', {})

def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

# ---------- Carrito ----------
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Book

def add_to_cart(request, book_id):
    # 🔥 Limpia el carrito viejo (solo para depuración)
    if 'cart' in request.session:
        old_cart = request.session['cart']
        if any(isinstance(v, dict) for v in old_cart.values()):
            request.session['cart'] = {}
            request.session.modified = True

    book = get_object_or_404(Book, pk=book_id)
    cart = request.session.get('cart', {})

    book_id_str = str(book_id)
    if book_id_str in cart:
        cart[book_id_str] += 1
    else:
        cart[book_id_str] = 1

    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, f"Agregado al carrito: {book.title}")
    return redirect('cart_view')



def update_cart(request, book_id):
    """Incrementa o decrementa cantidad. Si llega a 0, elimina el ítem."""
    if request.method != 'POST':
        return redirect('cart_view')

    action = request.POST.get('action')  # 'inc' | 'dec'
    cart = _get_cart(request)
    key = str(book_id)

    if key in cart:
        if action == 'inc':
            cart[key] += 1
        elif action == 'dec':
            cart[key] -= 1

        if cart[key] <= 0:
            del cart[key]
        _save_cart(request, cart)

    return redirect('cart_view')

def remove_from_cart(request, book_id):
    """Quita por completo el libro del carrito."""
    cart = _get_cart(request)
    key = str(book_id)
    if key in cart:
        del cart[key]
        _save_cart(request, cart)
        messages.success(request, "Libro eliminado del carrito 🗑️")
    else:
        messages.warning(request, "Ese libro no estaba en tu carrito.")
    return redirect('cart_view')

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    for book_id, value in cart.items():
        # ✅ Soporte tanto para {"quantity": 2} como para 2
        if isinstance(value, dict):
            qty = value.get("quantity", 1)
        else:
            qty = value

        try:
            book = Book.objects.get(pk=book_id)
            subtotal = float(book.price) * int(qty)
            cart_items.append({
                "book": book,
                "quantity": int(qty),
                "subtotal": round(subtotal, 2)
            })
            total_price += subtotal
        except Book.DoesNotExist:
            continue

    return render(request, "books/cart.html", {
        "cart_items": cart_items,
        "total_price": round(total_price, 2)
    })




# (Opcional, útil para depurar en desarrollo)
def clear_cart(request):
    _save_cart(request, {})
    messages.info(request, "Carrito limpiado.")
    return redirect('cart_view')

def buy_now(request, book_id):
    """Agrega el libro al carrito y redirige al checkout (por ahora al carrito)."""
    book = get_object_or_404(Book, pk=book_id)
    cart = request.session.get('cart', {})
    key = str(book_id)
    cart[key] = cart.get(key, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart_view')