from django.core.management.base import BaseCommand
from books.models import Book
from django.conf import settings
from openai import OpenAI
import numpy as np

class Command(BaseCommand):
    help = "Generate and store embeddings for all books in the database"

    def handle(self, *args, **options):
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        books = Book.objects.all()
        self.stdout.write(f"📚 Found {books.count()} books in the database")

        for idx, book in enumerate(books, start=1):
            # Si el libro no tiene título, lo saltamos
            if not book.title:
                continue

            # Generamos el texto base para el embedding
            text_parts = [
                book.title or "",
                f"Autor: {book.authors}" if book.authors else "",
                f"Género: {book.genre}" if book.genre else "",
                f"Editorial: {book.publisher}" if book.publisher else "",
            ]
            text = ". ".join(part for part in text_parts if part)

            # Generamos el embedding
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                emb_array = np.array(response.data[0].embedding, dtype=np.float32)

                # Guardamos el embedding como bytes
                book.emb = emb_array.tobytes()
                book.save(update_fields=["emb"])

                self.stdout.write(f"✅ ({idx}) Embedding guardado para: {book.title}")

            except Exception as e:
                self.stdout.write(f"❌ Error con '{book.title}': {str(e)}")
                continue

        self.stdout.write(self.style.SUCCESS("🎯 Todos los embeddings fueron generados correctamente"))
