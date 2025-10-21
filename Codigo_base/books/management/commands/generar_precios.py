from django.core.management.base import BaseCommand
from books.models import Book
import random
import locale

class Command(BaseCommand):
    help = 'Genera precios semi-realistas para los libros según su rating y longitud del título.'

    def handle(self, *args, **options):
        try:
            locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, '')  # fallback

        libros = Book.objects.all()
        total = libros.count()
        count = 0
        errors = 0

        if total == 0:
            self.stdout.write(self.style.WARNING('No hay libros en la base de datos.'))
            return

        self.stdout.write(self.style.WARNING(f'Iniciando generación de precios para {total} libros...\n'))

        for libro in libros:
            try:
                # Base aleatoria entre 20.000 y 80.000
                base = random.uniform(20000, 80000)

                # Ajustes según características
                ajuste_rating = (libro.average_rating or 0) * 3000
                ajuste_titulo = len(libro.title) * 50

                # Calcular y asignar precio
                precio = round(base + ajuste_rating + ajuste_titulo, -2)
                libro.precio = precio
                libro.save()
                count += 1

                if count % 1000 == 0:
                    self.stdout.write(self.style.SUCCESS(f'Generados {count} precios...'))

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.stderr.write(self.style.ERROR(f'Error al generar precio para "{libro.title}": {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Proceso completado: {count} libros actualizados, {errors} errores.'))
