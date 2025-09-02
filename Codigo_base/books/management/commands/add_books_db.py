from django.core.management.base import BaseCommand
import json
from books.models import Book
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Agrega libros desde el archivo books.json a la base de datos.'

    def handle(self, *args, **kwargs):
        try:
            with open('books/management/commands/books.json', encoding='utf-8') as f:
                books = json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error leyendo books.json: {e}'))
            return

        count = 0
        for book in books[:100]:
            try:
                Book.objects.create(
                    title=book.get('title', ''),
                    genre=book.get('genre', ''),
                    publication_year=book.get('publication_year'),
                    synopsis=book.get('synopsis', ''),
                    cover_image='books/images/default.jpg'  # Imagen por defecto
                )
                count += 1
            except IntegrityError as e:
                self.stderr.write(self.style.WARNING(f'No se pudo agregar el libro: {book.get("title", "")} - {e}'))
            except Exception as e:
                self.stderr.write(self.style.WARNING(f'Error inesperado con el libro: {book.get("title", "")} - {e}'))

        self.stdout.write(self.style.SUCCESS(f'Se agregaron {count} libros a la base de datos.'))
