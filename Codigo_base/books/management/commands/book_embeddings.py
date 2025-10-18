from django.core.management.base import BaseCommand
from books.models import Book
from django.conf import settings
from openai import OpenAI
import math
import time
from tqdm import tqdm  # 💪 barra de progreso opcional (instalar con `pip install tqdm`)

class Command(BaseCommand):
    help = "⚡ Genera embeddings por lotes (más rápido y eficiente) y los guarda en formato JSON."

    def handle(self, *args, **options):
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # 🔍 Buscar libros que aún no tengan embeddings
        books = list(Book.objects.filter(embeddings__isnull=True))
        total = len(books)
        batch_size = 100  # 🔥 Ajustá este valor según tu velocidad o límite de tokens
        num_batches = math.ceil(total / batch_size)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("✅ No hay libros pendientes para generar embeddings."))
            return

        self.stdout.write(f"📚 Libros pendientes: {total}")
        self.stdout.write(f"🧩 Procesando en {num_batches} lotes de hasta {batch_size} libros cada uno\n")

        # 🌀 Iterar sobre lotes con barra de progreso
        for i in range(num_batches):
            batch = books[i * batch_size:(i + 1) * batch_size]
            texts, ids = [], []

            for book in batch:
                text_parts = [
                    book.title or "",
                    f"Autor: {book.authors}" if book.authors else "",
                    f"Género: {book.genre}" if book.genre else "",
                    f"Editorial: {book.publisher}" if book.publisher else "",
                ]
                text = ". ".join(part for part in text_parts if part).strip()
                if text:
                    texts.append(text)
                    ids.append(book.id)

            if not texts:
                continue

            try:
                # 🚀 Llamada masiva a la API de embeddings
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )

                # 💾 Guardar embeddings como JSON
                for j, emb_data in enumerate(response.data):
                    book_id = ids[j]
                    embedding = emb_data.embedding
                    book = next(b for b in batch if b.id == book_id)
                    book.embeddings = embedding
                    book.save(update_fields=["embeddings"])

                self.stdout.write(f"✅ Lote {i+1}/{num_batches} completado ({len(batch)} libros)")
                time.sleep(1.5)  # ⏱️ Pausa ligera para evitar límite de velocidad

            except Exception as e:
                self.stderr.write(f"❌ Error en lote {i+1}: {str(e)}")
                time.sleep(5)
                continue

        self.stdout.write(self.style.SUCCESS("🎯 Todos los embeddings fueron generados y guardados exitosamente"))
