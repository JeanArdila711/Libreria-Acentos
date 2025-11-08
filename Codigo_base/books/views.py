from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView
from django.db.models import Q, Count
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
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
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

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
        
        # 🆕 RECOMENDACIONES PERSONALIZADAS (si el usuario está autenticado)
        if self.request.user.is_authenticated:
            recommended_books = self.get_personalized_recommendations(self.request.user)
            ctx['personalized_books'] = recommended_books
        else:
            # Si no está autenticado, mostrar libros random
            from random import sample
            all_books = list(Book.objects.all())
            ctx['personalized_books'] = sample(all_books, min(len(all_books), 8))
        
        # 🆕 ÚLTIMAS RESEÑAS (5 más recientes)
        ctx['latest_reviews'] = Review.objects.select_related('user', 'book').order_by('-created_at')[:5]
        
        # Estadísticas
        ctx['total_books'] = Book.objects.count()
        ctx['total_reviews'] = Review.objects.count()
        
        return ctx
    
    def get_personalized_recommendations(self, user):
        """
        Genera recomendaciones personalizadas basadas en:
        1. Historial de compras
        2. Favoritos
        3. Reseñas que ha hecho
        """
        recommended_books = []
        
        try:
            # Obtener libros favoritos del usuario
            favorite_books = Book.objects.filter(
                id__in=Favorite.objects.filter(user=user).values_list('book_id', flat=True)
            ).exclude(embeddings__isnull=True)
            
            # Obtener libros comprados
            purchased_books = Book.objects.filter(
                id__in=OrderItem.objects.filter(
                    order__user=user
                ).values_list('book_id', flat=True)
            ).exclude(embeddings__isnull=True)
            
            # Obtener libros que ha reseñado
            reviewed_books = Book.objects.filter(
                id__in=Review.objects.filter(user=user).values_list('book_id', flat=True)
            ).exclude(embeddings__isnull=True)
            
            # Combinar todos los libros base
            base_books = list(favorite_books) + list(purchased_books) + list(reviewed_books)
            
            if base_books:
                # Calcular promedio de embeddings de libros base
                embeddings_list = []
                for book in base_books:
                    if book.embeddings:
                        embeddings_list.append(np.array(book.embeddings, dtype=np.float32))
                
                if embeddings_list:
                    # Promedio de embeddings
                    avg_embedding = np.mean(embeddings_list, axis=0)
                    
                    # Buscar libros similares
                    books_with_similarity = []
                    
                    # Excluir libros que ya tiene
                    exclude_ids = [b.id for b in base_books]
                    
                    for candidate in Book.objects.exclude(id__in=exclude_ids).exclude(embeddings__isnull=True)[:200]:
                        try:
                            candidate_emb = np.array(candidate.embeddings, dtype=np.float32)
                            similarity = cosine_similarity(avg_embedding, candidate_emb)
                            books_with_similarity.append((candidate, similarity))
                        except Exception:
                            continue
                    
                    # Ordenar por similitud
                    books_with_similarity.sort(key=lambda x: x[1], reverse=True)
                    recommended_books = [b[0] for b in books_with_similarity[:8]]
        
        except Exception as e:
            print(f"Error en recomendaciones personalizadas: {e}")
        
        # Si no hay suficientes recomendaciones, completar con mejor valorados
        if len(recommended_books) < 8:
            additional = Book.objects.filter(
                average_rating__isnull=False
            ).exclude(
                id__in=[b.id for b in recommended_books]
            ).order_by('-average_rating')[:8 - len(recommended_books)]
            
            recommended_books.extend(list(additional))
        
        return recommended_books[:8]



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
    
    # Obtener reseñas del libro
    reviews = Review.objects.filter(book=book).select_related('user')
    
    # Verificar si el usuario ya dejó reseña
    user_review = None
    if request.user.is_authenticated:
        try:
            user_review = Review.objects.get(book=book, user=request.user)
        except Review.DoesNotExist:
            pass
    
    # 🆕 LIBROS SIMILARES (usando embeddings)
    similar_books = []
    if book.embeddings:
        try:
            book_emb = np.array(book.embeddings, dtype=np.float32)
            books_with_similarity = []
            
            for other_book in Book.objects.exclude(id=book.id).exclude(embeddings__isnull=True)[:100]:
                try:
                    other_emb = np.array(other_book.embeddings, dtype=np.float32)
                    similarity = cosine_similarity(book_emb, other_emb)
                    books_with_similarity.append((other_book, similarity))
                except Exception:
                    continue
            
            books_with_similarity.sort(key=lambda x: x[1], reverse=True)
            similar_books = [b[0] for b in books_with_similarity[:6]]
        except Exception:
            pass
    
    # Si no hay similares por embeddings, usar mismo género
    if not similar_books and book.genre:
        similar_books = Book.objects.filter(
            genre=book.genre
        ).exclude(id=book.id).order_by('-average_rating')[:6]
    
    context = {
        "book": book,
        "reviews": reviews,
        "user_review": user_review,
        "similar_books": similar_books,
    }
    
    return render(request, "books/book_detail.html", context)



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

from django.db.models import Avg
from .models import Review

# ==========================================
# 📝 AGREGAR/EDITAR RESEÑA
# ==========================================
@login_required
def add_review(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if not rating or not comment:
            messages.error(request, "Debes agregar una calificación y comentario")
            return redirect('book_detail', book_id=book_id)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            messages.error(request, "La calificación debe ser entre 1 y 5")
            return redirect('book_detail', book_id=book_id)
        
        # Crear o actualizar reseña
        review, created = Review.objects.update_or_create(
            book=book,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        
        # Actualizar promedio del libro
        avg_rating = Review.objects.filter(book=book).aggregate(Avg('rating'))['rating__avg']
        book.average_rating = avg_rating
        book.ratings_count = Review.objects.filter(book=book).count()
        book.save(update_fields=['average_rating', 'ratings_count'])
        
        if created:
            messages.success(request, "✓ Reseña agregada exitosamente")
        else:
            messages.success(request, "✓ Reseña actualizada exitosamente")
        
        return redirect('book_detail', book_id=book_id)
    
    return redirect('book_detail', book_id=book_id)


# ==========================================
# 🗑️ ELIMINAR RESEÑA
# ==========================================
@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    book = review.book
    review.delete()
    
    # Recalcular promedio
    avg_rating = Review.objects.filter(book=book).aggregate(Avg('rating'))['rating__avg']
    book.average_rating = avg_rating if avg_rating else None
    book.ratings_count = Review.objects.filter(book=book).count()
    book.save(update_fields=['average_rating', 'ratings_count'])
    
    messages.success(request, "✓ Reseña eliminada")
    return redirect('book_detail', book_id=book.id)


# ==========================================
# 👍 MARCAR RESEÑA COMO ÚTIL
# ==========================================
@login_required
def mark_review_helpful(request, review_id):
    review = get_object_or_404(Review, pk=review_id)
    review.helpful_count += 1
    review.save(update_fields=['helpful_count'])
    messages.success(request, "✓ Gracias por tu valoración")
    return redirect('book_detail', book_id=review.book.id)

# ==========================================
# Recomendaciones con IA
# ==========================================

@login_required
def personalized_recommendations_view(request):
    """
    Página dedicada a recomendaciones personalizadas
    """
    user = request.user
    
    # Obtener libros favoritos
    favorite_books = Book.objects.filter(
        id__in=Favorite.objects.filter(user=user).values_list('book_id', flat=True)
    )
    
    # Obtener historial de compras
    purchased_books = Book.objects.filter(
        id__in=OrderItem.objects.filter(
            order__user=user
        ).values_list('book_id', flat=True)
    ).distinct()
    
    # Generar recomendaciones
    recommended_books = []
    
    try:
        base_books = list(favorite_books) + list(purchased_books)
        
        if base_books:
            embeddings_list = []
            for book in base_books:
                if book.embeddings:
                    embeddings_list.append(np.array(book.embeddings, dtype=np.float32))
            
            if embeddings_list:
                avg_embedding = np.mean(embeddings_list, axis=0)
                books_with_similarity = []
                
                exclude_ids = [b.id for b in base_books]
                
                for candidate in Book.objects.exclude(id__in=exclude_ids).exclude(embeddings__isnull=True)[:300]:
                    try:
                        candidate_emb = np.array(candidate.embeddings, dtype=np.float32)
                        similarity = cosine_similarity(avg_embedding, candidate_emb)
                        books_with_similarity.append((candidate, similarity))
                    except Exception:
                        continue
                
                books_with_similarity.sort(key=lambda x: x[1], reverse=True)
                recommended_books = [b[0] for b in books_with_similarity[:20]]
    
    except Exception as e:
        print(f"Error: {e}")
    
    # Completar con mejor valorados si faltan
    if len(recommended_books) < 20:
        additional = Book.objects.filter(
            average_rating__isnull=False
        ).exclude(
            id__in=[b.id for b in recommended_books]
        ).order_by('-average_rating')[:20 - len(recommended_books)]
        
        recommended_books.extend(list(additional))
    
    context = {
        'recommended_books': recommended_books,
        'base_books_count': len(base_books) if 'base_books' in locals() else 0,
    }
    
    return render(request, 'books/personalized_recommendations.html', context)


# ==========================================
# 🛒 CHECKOUT - PROCESO DE PAGO
# ==========================================
@login_required
def checkout_view(request):
    """Vista de checkout donde el usuario ingresa dirección de envío"""
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, "Tu carrito está vacío")
        return redirect('cart_view')

    # Calcular items del carrito
    cart_items = []
    total = 0

    for book_id_str, qty in cart.items():
        try:
            qty = int(qty)
            book = Book.objects.get(pk=int(book_id_str))
            price = float(book.precio or 0)
            subtotal = price * qty
            total += subtotal

            cart_items.append({
                'book': book,
                'quantity': qty,
                'price': price,
                'subtotal': subtotal
            })
        except (Book.DoesNotExist, ValueError):
            continue

    if request.method == 'POST':
        # Obtener todos los campos del formulario
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        cedula = request.POST.get('cedula', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        apartamento = request.POST.get('apartamento', '').strip()
        ciudad = request.POST.get('ciudad', '').strip()
        provincia = request.POST.get('provincia', '').strip()
        codigo_postal = request.POST.get('codigo_postal', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        pais = request.POST.get('pais', 'Colombia')

        # Validar campos requeridos
        if not all([nombre, apellidos, cedula, direccion, ciudad, provincia, telefono]):
            messages.error(request, "Por favor completa todos los campos requeridos")
            return render(request, 'books/checkout.html', {
                'cart_items': cart_items,
                'total': total
            })

        # Construir dirección completa
        shipping_address = f"{nombre} {apellidos}\nCC: {cedula}\n{direccion}"
        if apartamento:
            shipping_address += f", {apartamento}"
        shipping_address += f"\n{ciudad}, {provincia}"
        if codigo_postal:
            shipping_address += f" - {codigo_postal}"
        shipping_address += f"\n{pais}\nTel: {telefono}"

        # Guardar dirección en la sesión
        request.session['shipping_address'] = shipping_address
        request.session.modified = True

        # Redirigir a la página de selección de método de pago
        return redirect('payment_method')

    context = {
        'cart_items': cart_items,
        'total': total
    }

    return render(request, 'books/checkout.html', context)


@login_required
def payment_method_view(request):
    """Vista de selección de método de pago"""
    cart = request.session.get('cart', {})
    shipping_address = request.session.get('shipping_address', '')

    if not cart:
        messages.error(request, "Tu carrito está vacío")
        return redirect('cart_view')

    if not shipping_address:
        messages.error(request, "Por favor completa primero la información de envío")
        return redirect('checkout')

    # Calcular total del carrito
    cart_items = []
    total = 0

    for book_id_str, qty in cart.items():
        try:
            qty = int(qty)
            book = Book.objects.get(pk=int(book_id_str))
            price = float(book.precio or 0)
            subtotal = price * qty
            total += subtotal

            cart_items.append({
                'book': book,
                'quantity': qty,
                'price': price,
                'subtotal': subtotal
            })
        except (Book.DoesNotExist, ValueError):
            continue

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')

        if not payment_method:
            messages.error(request, "Por favor selecciona un método de pago")
            return render(request, 'books/payment_method.html', {
                'cart_items': cart_items,
                'total': total,
                'payment_methods': Order.PAYMENT_METHOD_CHOICES
            })

        # Redirigir a la página de procesamiento de pago
        return redirect('process_payment', payment_method=payment_method)

    context = {
        'cart_items': cart_items,
        'total': total,
        'payment_methods': Order.PAYMENT_METHOD_CHOICES,
        'shipping_address': shipping_address
    }

    return render(request, 'books/payment_method.html', context)


@login_required
def process_payment_view(request, payment_method):
    """Vista de procesamiento de pago"""
    cart = request.session.get('cart', {})
    shipping_address = request.session.get('shipping_address', '')

    if not cart:
        messages.error(request, "Tu carrito está vacío")
        return redirect('cart_view')

    if not shipping_address:
        messages.error(request, "Por favor completa primero la información de envío")
        return redirect('checkout')

    # Calcular items y total
    order_items_data = []
    total = 0

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

    if request.method == 'POST':
        # Aquí se procesaría el pago con la pasarela real
        # Por ahora simularemos el procesamiento

        import uuid
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        # Crear pedido
        order = Order.objects.create(
            user=request.user,
            total_price=total,
            shipping_address=shipping_address,
            payment_method=payment_method,
            payment_status='completed',
            transaction_id=transaction_id,
            paid_at=timezone.now()
        )

        # Crear items del pedido
        for item_data in order_items_data:
            OrderItem.objects.create(
                order=order,
                book=item_data['book'],
                quantity=item_data['quantity'],
                price=item_data['price']
            )

        # Limpiar carrito y sesión
        request.session['cart'] = {}
        if 'shipping_address' in request.session:
            del request.session['shipping_address']
        request.session.modified = True

        messages.success(request, f"✓ ¡Pago procesado exitosamente! Pedido #{order.order_number}")
        return redirect('payment_success', order_id=order.id)

    # Mostrar formulario de pago según el método seleccionado
    context = {
        'payment_method': payment_method,
        'payment_method_display': dict(Order.PAYMENT_METHOD_CHOICES).get(payment_method, payment_method),
        'total': total,
        'shipping_address': shipping_address
    }

    return render(request, 'books/process_payment.html', context)


@login_required
def payment_success_view(request, order_id):
    """Vista de confirmación de pago exitoso"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        'order': order
    }

    return render(request, 'books/payment_success.html', context)


