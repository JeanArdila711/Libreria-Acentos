from django.core.management.base import BaseCommand
from books.models import Book
import csv
from pathlib import Path

class Command(BaseCommand):
    help = 'Importa libros desde un archivo books.csv al modelo Book.'

    def handle(self, *args, **options):
        # Cambia el path al nuevo dataset si es necesario
        csv_path = Path(__file__).resolve().parent.parent.parent.parent / 'books.csv'
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f'Archivo no encontrado: {csv_path}'))
            return

        # Eliminar todos los libros existentes para evitar duplicados
        Book.objects.all().delete()
        self.stdout.write(self.style.WARNING('Se eliminaron todos los libros existentes.'))

        with open(csv_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            errors = 0
            for row in reader:
                try:
                    book = Book(
                        isbn=row.get('ISBN', ''),
                        title=row.get('Book-Title', ''),
                        authors=row.get('Book-Author', ''),
                        publication_date=row.get('Year-Of-Publication', ''),
                        publisher=row.get('Publisher', ''),
                        image_url=row.get('Image-URL-M', ''),
                        average_rating=float(row.get('Average-Book-Rating')) if row.get('Average-Book-Rating') else None,
                        ratings_count=int(row.get('Rating-Count')) if row.get('Rating-Count') else None,
                        dominant_age_group=row.get('Dominant-Age-Group', ''),
                        genre=row.get('Genre', 'Sin género'),
                        description=row.get('Description', ''),
                    )
                    book.save()
                    count += 1
                    if count % 1000 == 0:
                        self.stdout.write(self.style.SUCCESS(f'Importados {count} libros...'))
                except Exception as e:
                    errors += 1
                    if errors <= 10:  # Solo mostrar los primeros 10 errores
                        self.stderr.write(self.style.ERROR(f'Error en fila {count+1}: {e}'))

            self.stdout.write(self.style.SUCCESS(f'Proceso completado: {count} libros importados, {errors} errores.'))
