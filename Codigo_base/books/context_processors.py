from .models import Book

def common_context(request):
    # Obtener valores únicos para los filtros
    genres = Book.objects.values_list('genre', flat=True).distinct().order_by('genre')
    authors = Book.objects.values_list('author', flat=True).distinct().order_by('author')
    # Para el año, asumimos que puedes tener un campo 'publication_year' o lo extraemos del título/sinopsis si no tienes uno específico.
    # Por ahora, para simplificar, si no tienes campo de año, no lo incluimos o ponemos uno de ejemplo.
    # Si agregas un campo 'publication_year' a tu modelo Book, descomenta la siguiente línea:
    # years = Book.objects.values_list('publication_year', flat=True).distinct().order_by('publication_year')

    return {
        'app_name': "BiblioSphere",
        'student_name': "Tomas Posada Suarez",
        'all_genres': genres,
        'all_authors': authors,
        # 'all_years': years, # Descomentar si agregas el campo 'publication_year' al modelo Book
    }