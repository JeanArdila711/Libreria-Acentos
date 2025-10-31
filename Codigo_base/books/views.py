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
# 🔧 CONFIGURACIÓN OPENAI
# -------------------------------------------------------
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'openAI.env'))

def get_openai_client():
    """Inicializa el cliente de OpenAI usando la API Key del entorno."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("❌ No se encontró la API key de OpenAI en las variables de entorno.")
    return OpenAI(api_key=api_key)


def cosine_similarity(a, b):
    """Calcula la similitud de coseno entre dos vectores."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


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
            authors__regex=r'(' + '|'.join([a.replace('.', r'\.') for a in authors]) + ')'
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
        
        # Top 4 mejor valorados
        ctx['top_rated_books'] = Book.objects.filter(
            average_rating__isnull=False
        ).order_by('-average_rating')[:4]
        
        # Últimos 8 agregados (novedades)
        ctx['new_books'] = Book.objects.all().order_by('-id')[:8]
        
        # Featured books (para explorar por género)
        ctx['featured_books'] = Book.objects.all()[:16]
        
        # Estadísticas
        ctx['total_books'] = Book.objects.count()
        
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
        
        # Géneros
        context['genres'] = Book.objects.values_list('genre', flat=True).exclude(genre='').distinct().order_by('genre')

        # Autores
        autores_raw = Book.objects.values_list('authors', flat=True).exclude(authors='').distinct()
        autores_set = set()
        for autores in autores_raw:
            for autor in autores.split('/'):
                autores_set.add(autor.strip())
        context['authors'] = sorted(autores_set)

        # Filtros seleccionados
        request = self.request
        context['selected_genres'] = request.GET.getlist('genre')
        context['selected_authors'] = request.GET.getlist('author')
        
        # Contar filtros activos
        active_filters = 0
        if request.GET.get('q'):
            active_filters += 1
        if request.GET.getlist('genre'):
            active_filters += len(request.GET.getlist('genre'))
        if request.GET.getlist('author'):
            active_filters += len(request.GET.getlist('author'))
        if request.GET.get('price_range'):
            active_filters += 1
        if request.GET.get('rating'):
            active_filters += 1
        if request.GET.get('year'):
            active_filters += 1
        
        context['active_filters_count'] = active_filters

        top_4_books = Book.objects.filter(
            average_rating__isnull=False
        ).order_by('-average_rating')[:4]

        context['top_4_books'] = top_4_books
        
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        request = self.request
        
        # 🔍 Búsqueda por texto
        search = request.GET.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(authors__icontains=search) |
                Q(genre__icontains=search)
            )

        # 📚 Filtro por Género
        genres = request.GET.getlist('genre')
        if genres:
            qs = qs.filter(genre__in=genres)

        # 👤 Filtro por Autor
        authors = request.GET.getlist('author')
        if authors:
            qs = qs.filter(authors__in=authors)

        # 💰 Filtro por Rango de Precio
        price_range = request.GET.get('price_range', '').strip()
        if price_range:
            try:
                min_price, max_price = map(int, price_range.split('-'))
                qs = qs.filter(precio__gte=min_price, precio__lte=max_price)
            except ValueError:
                pass

        # ⭐ Filtro por Rating
        rating = request.GET.get('rating', '').strip()
        if rating:
            try:
                rating_value = float(rating)
                qs = qs.filter(average_rating__gte=rating_value)
            except ValueError:
                pass

        # 📅 Filtro por Año
        year_range = request.GET.get('year', '').strip()
        if year_range:
            try:
                start_year, end_year = map(int, year_range.split('-'))
                qs = qs.filter(publication_date__gte=start_year, publication_date__lte=end_year)
            except ValueError:
                pass

        # 📊 Ordenamiento
        sort_by = request.GET.get('sort_by', '').strip()
        
        if sort_by == 'price_low':
            qs = qs.order_by('precio')
        elif sort_by == 'price_high':
            qs = qs.order_by('-precio')
        elif sort_by == 'rating_high':
            qs = qs.order_by('-average_rating')
        elif sort_by == 'rating_low':
            qs = qs.order_by('average_rating')
        elif sort_by == 'year_new':
            qs = qs.order_by('-publication_date')
        elif sort_by == 'year_old':
            qs = qs.order_by('publication_date')
        elif sort_by == 'title_az':
            qs = qs.order_by('title')
        elif sort_by == 'title_za':
            qs = qs.order_by('-title')
        else:
            # Orden por defecto
            qs = qs.order_by('title')

        return qs
    
class Top100BooksView(ListView):
    model = Book
    template_name = "books/top_100.html"
    context_object_name = "top_books"
    paginate_by = 20

    def get_queryset(self):
        return Book.objects.filter(
            average_rating__isnull=False
        ).order_by('-average_rating')[:100]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = 100
        return context




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
    book_counts_by_year = {}
    for book in all_books:
        year = str(book.publication_date) if book.publication_date else "Sin año"
        book_counts_by_year[year] = book_counts_by_year.get(year, 0) + 1

    book_counts_by_genre = {}
    for book in all_books:
        genre = book.genre if book.genre else "Sin género"
        book_counts_by_genre[genre] = book_counts_by_genre.get(genre, 0) + 1

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
@csrf_exempt
def recommend_book(request):
    if request.method == "POST":
        prompt = request.POST.get("prompt", "").strip()
        if not prompt:
            return render(request, "books/recommend.html", {
                "error": "Por favor escribe una descripción o preferencia.",
                "show_prompt_section": True
            })

        try:
            client = get_openai_client()  # ✅ Se inicializa aquí

            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[prompt]
            )
            prompt_emb = np.array(response.data[0].embedding, dtype=np.float32)

            books_with_similarity = []
            for book in Book.objects.exclude(embeddings__isnull=True):
                try:
                    if not book.embeddings:
                        continue
                    book_emb = np.array(book.embeddings, dtype=np.float32)
                    similarity = cosine_similarity(prompt_emb, book_emb)
                    books_with_similarity.append((book, similarity))
                except Exception:
                    continue

            books_with_similarity.sort(key=lambda x: x[1], reverse=True)
            top_books = books_with_similarity[:5]

            if not top_books:
                return render(request, "books/recommend.html", {
                    "prompt": prompt,
                    "message": "No se encontraron coincidencias.",
                    "show_prompt_section": True
                })

            context = {
                "prompt": prompt,
                "recommendations": [
                    {"book": b, "similarity": round(float(s), 4)} for b, s in top_books
                ]
            }
            return render(request, "books/recommend.html", context)

        except Exception as e:
            return render(request, "books/recommend.html", {
                "error": f"Ocurrió un error: {e}",
                "show_prompt_section": True
            })

    # 👇 Cuando entra por primera vez (GET)
    return render(request, "books/recommend.html", {
        "show_prompt_section": True
    })


# -------------------------------------------------------
# 4️⃣ CARRITO DE COMPRAS
# -------------------------------------------------------
def _get_qty(value):
    """Devuelve cantidad válida sin importar el formato viejo o nuevo."""
    if isinstance(value, dict):
        return int(value.get("quantity", 1))
    return int(value)


def add_to_cart(request, book_id):
    cart = request.session.get('cart', {})
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

    messages.success(request, f"✓ {book.title} agregado al carrito")
    
    # Redirigir a la página anterior en lugar del carrito
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        return redirect('book_detail', book_id=book_id)



def update_cart(request, book_id, action):
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
    cart = request.session.get('cart', {})
    key = str(book_id)
    if key in cart:
        del cart[key]
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, "Libro eliminado del carrito 🗑️")
    return redirect('cart_view')


def cart_view(request):
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

        # ✅ Usamos el nuevo campo "precio"
        price = float(book.precio or 0.0)
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
    request.session['cart'] = {}
    request.session.modified = True
    messages.info(request, "Carrito vaciado 🧹")
    return redirect('cart_view')


def buy_now(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    cart = request.session.get('cart', {})
    key = str(book_id)
    cart[key] = cart.get(key, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart_view')


# --------- USER PROFILE ------------

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View

@method_decorator(login_required, name='dispatch')
class UserProfileView(View):
    template_name = "users/profile.html"

    def get(self, request):
        return render(request, self.template_name, {"user": request.user})

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Sum, Count
from .models import Favorite, Order, OrderItem, UserProfile
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

# ==========================================
# 🔹 VISTA DE PERFIL CON PESTAÑAS
# ==========================================
@method_decorator(login_required, name='dispatch')
class UserProfileView(View):
    template_name = "users/profile.html"

    def get(self, request):
        # Obtener o crear perfil del usuario
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Estadísticas del usuario
        total_orders = Order.objects.filter(user=request.user).count()
        total_spent = Order.objects.filter(user=request.user).aggregate(
            total=Sum('total_price')
        )['total'] or 0
        total_favorites = Favorite.objects.filter(user=request.user).count()
        
        # Último pedido
        last_order = Order.objects.filter(user=request.user).first()
        
        context = {
            "user": request.user,
            "profile": profile,
            "total_orders": total_orders,
            "total_spent": total_spent,
            "total_favorites": total_favorites,
            "last_order": last_order,
        }
        return render(request, self.template_name, context)


# ==========================================
# 🔹 EDITAR PERFIL
# ==========================================
@login_required
def edit_profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Actualizar información del usuario
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Actualizar perfil
        profile.phone = request.POST.get('phone', '')
        profile.bio = request.POST.get('bio', '')
        
        # Manejar foto de perfil
        if request.FILES.get('avatar'):
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        
        messages.success(request, "✓ Perfil actualizado correctamente")
        return redirect('user_profile')
    
    return render(request, 'users/edit_profile.html', {'profile': profile})


# ==========================================
# 🔹 MIS PEDIDOS
# ==========================================
@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__book')
    return render(request, 'users/orders.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'users/order_detail.html', {'order': order})


# ==========================================
# 🔹 FAVORITOS
# ==========================================
@login_required
def my_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book')
    return render(request, 'users/favorites.html', {'favorites': favorites})


@login_required
def toggle_favorite(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, book=book)
    
    if not created:
        favorite.delete()
        messages.success(request, f"❤️ {book.title} eliminado de favoritos")
    else:
        messages.success(request, f"❤️ {book.title} agregado a favoritos")
    
    # Redirigir a la página anterior
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        return redirect('book_detail', book_id=book_id)


# ==========================================
# 🔹 ESTADÍSTICAS
# ==========================================
@login_required
def user_statistics(request):
    # Estadísticas generales
    total_orders = Order.objects.filter(user=request.user).count()
    total_spent = Order.objects.filter(user=request.user).aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    # Géneros más comprados
    genre_stats = OrderItem.objects.filter(order__user=request.user).values(
        'book__genre'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Autores más comprados
    author_stats = OrderItem.objects.filter(order__user=request.user).values(
        'book__authors'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Determinar nivel de usuario
    if total_orders == 0:
        level = "Nuevo"
        level_icon = "🌱"
    elif total_orders < 5:
        level = "Bronce"
        level_icon = "🥉"
    elif total_orders < 15:
        level = "Plata"
        level_icon = "🥈"
    else:
        level = "Oro"
        level_icon = "🥇"
    
    context = {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'genre_stats': genre_stats,
        'author_stats': author_stats,
        'level': level,
        'level_icon': level_icon,
    }
    
    return render(request, 'users/statistics.html', context)


# ==========================================
# 🔹 CONFIGURACIÓN Y PREFERENCIAS
# ==========================================
@login_required
def user_settings(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Actualizar preferencias
        profile.email_notifications = request.POST.get('email_notifications') == 'on'
        profile.newsletter = request.POST.get('newsletter') == 'on'
        profile.new_releases_alert = request.POST.get('new_releases_alert') == 'on'
        profile.discount_alerts = request.POST.get('discount_alerts') == 'on'
        profile.save()
        
        messages.success(request, "✓ Preferencias guardadas correctamente")
        return redirect('user_settings')
    
    return render(request, 'users/settings.html', {'profile': profile})


# ==========================================
# 🔹 CREAR PEDIDO DESDE EL CARRITO
# ==========================================
@login_required
def create_order_from_cart(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        
        if not cart:
            messages.error(request, "Tu carrito está vacío")
            return redirect('cart_view')
        
        # Calcular total
        total = 0
        order_items_data = []
        
        for book_id_str, qty in cart.items():
            try:
                qty = int(qty)
                book = Book.objects.get(pk=int(book_id_str))
                price = float(book.precio or 0)
                subtotal = price * qty
                total += subtotal
                
                order_items_data.append({
                    'book': book,
                    'quantity': qty,
                    'price': price
                })
            except (Book.DoesNotExist, ValueError):
                continue
        
        # Crear pedido
        order = Order.objects.create(
            user=request.user,
            total_price=total,
            shipping_address=request.POST.get('shipping_address', '')
        )
        
        # Crear items del pedido
        for item_data in order_items_data:
            OrderItem.objects.create(
                order=order,
                book=item_data['book'],
                quantity=item_data['quantity'],
                price=item_data['price']
            )
        
        # Limpiar carrito
        request.session['cart'] = {}
        request.session.modified = True
        
        messages.success(request, f"✓ Pedido #{order.order_number} creado exitosamente")
        return redirect('order_detail', order_id=order.id)
    
    return redirect('cart_view')
