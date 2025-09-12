from django.core.management.base import BaseCommand
from books.models import Book
import csv
from pathlib import Path

class Command(BaseCommand):
    help = 'Importa libros desde un archivo Books.csv al modelo Book.'

    def handle(self, *args, **options):
        # Cambia el path al nuevo dataset si es necesario
        csv_path = Path(__file__).resolve().parent.parent.parent.parent / 'books_dataset.csv'
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f'Archivo no encontrado: {csv_path}'))
            return
        with open(csv_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                try:
                    book = Book(
                        book_id=int(row.get('bookID')) if row.get('bookID') else None,
                        title=row.get('title', ''),
                        authors=row.get('authors', ''),
                        average_rating=float(row.get('average_rating')) if row.get('average_rating') else None,
                        isbn=row.get('isbn', ''),
                        isbn13=row.get('isbn13', ''),
                        language_code=row.get('language_code', '').strip(),
                        num_pages=int(row.get('num_pages')) if row.get('num_pages') else None,
                        ratings_count=int(row.get('ratings_count')) if row.get('ratings_count') else None,
                        text_reviews_count=int(row.get('text_reviews_count')) if row.get('text_reviews_count') else None,
                        publication_date=row.get('publication_date', ''),
                        publisher=row.get('publisher', ''),
                        genre=row.get('genre', ''),
                        price=float(row.get('price_COP')) if row.get('price_COP') else None,
                    )
                    book.save()
                    count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'Error en fila {count+1}: {e}'))
            self.stdout.write(self.style.SUCCESS(f'Se importaron {count} libros.'))
