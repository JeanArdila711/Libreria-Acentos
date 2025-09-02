import csv
from pathlib import Path
import random
from django.core.management.base import BaseCommand
from django.conf import settings
from books.models import Book


class Command(BaseCommand):
    help = "Carga o actualiza libros desde books.csv ubicado en BASE_DIR"

    def add_arguments(self, parser):
        parser.add_argument("--file", dest="file", default=None, help="Ruta al CSV (opcional)")
        parser.add_argument("--truncate", action="store_true", help="Borrar libros antes de cargar")

    def handle(self, *args, **options):
        csv_path = options.get("file")
        if csv_path:
            csv_file = Path(csv_path)
        else:
            csv_file = Path(settings.BASE_DIR) / "books.csv"

        if not csv_file.exists():
            self.stderr.write(self.style.ERROR(f"No se encontró el CSV en: {csv_file}"))
            return

        if options.get("truncate"):
            Book.objects.all().delete()
            self.stdout.write(self.style.WARNING("Tabla Book vaciada"))

        created = 0
        updated = 0
        def classify_genre(title: str, description: str, authors: str) -> str:
            t = (title or "").lower()
            d = (description or "").lower()
            a = (authors or "").lower()
            text = f"{t} {d} {a}"
            checks = [
                ("Fantasía", ["harry potter", "fantasy", "witch", "wizard", "dragon", "hobbit", "ring"]),
                ("Ciencia Ficción", ["sci-fi", "science fiction", "robot", "space", "galaxy", "dune"]),
                ("Distopía", ["dystopia", "dystopian", "1984", "hunger games", "maze runner"]),
                ("Romance", ["romance", "love", "romántic", "pride and prejudice"]),
                ("Misterio", ["mystery", "detective", "sherlock", "case of", "whodunit"]),
                ("Thriller", ["thriller", "suspense", "conspiracy", "spy"]),
                ("Crimen", ["crime", "noir", "murder", "serial killer"]),
                ("Horror", ["horror", "terror", "vampire", "dracula"]),
                ("Historia", ["history", "historical", "wwii", "world war", "revolution"]),
                ("Biografía", ["biography", "memoir", "autobiography"]),
                ("Clásicos", ["classic", "don quixote", "moby dick", "odyssey", "iliad"]),
                ("Infantil", ["children", "kids", "picture book"]),
                ("Juvenil", ["young adult", "ya novel"]),
                ("Aventura", ["adventure", "journey", "quest"]),
                ("Filosofía", ["philosophy", "ethics"]),
                ("Poesía", ["poetry", "poems"]),
            ]
            for label, kws in checks:
                if any(k in text for k in kws):
                    return label
            return "General"

        with csv_file.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title") or row.get("Title")
                if not title:
                    continue
                # Imagen: preferir https; si no hay, usar placeholder
                image = (row.get("image_url") or row.get("cover_image", "")).strip()
                if image.startswith("http://"):
                    image = "https://" + image[len("http://"):]
                # Fallback a OpenLibrary por ISBN si no hay imagen utilizable
                if not image:
                    isbn = (row.get("isbn") or "").strip()
                    if isbn:
                        image = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
                    else:
                        image = "https://placehold.co/300x450?text=Sin+Imagen"

                # Precio sintético si el dataset no lo trae
                # Basado en longitud del título y rating si existe (con límites)
                try:
                    rating = float(row.get("average_rating") or 0)
                except Exception:
                    rating = 0
                base_price = 8.0 + (len(title) % 12) * 0.8 + rating
                price = round(min(max(base_price, 7.5), 45.0), 2)
                authors = row.get("authors") or row.get("author", "")
                description = row.get("description") or row.get("synopsis", "")
                inferred_genre = row.get("genres") or row.get("genre", "")
                if not inferred_genre:
                    inferred_genre = classify_genre(title, description, authors)

                defaults = {
                    "author": authors,
                    "genre": inferred_genre,
                    "publication_year": int(row.get("original_publication_year") or 0) or None,
                    "cover_image": image,
                    "synopsis": description,
                    "price": price,
                }
                obj, is_created = Book.objects.update_or_create(
                    title=title,
                    defaults=defaults,
                )
                created += 1 if is_created else 0
                updated += 0 if is_created else 1

        self.stdout.write(self.style.SUCCESS(
            f"Carga completada. Nuevos: {created}, Actualizados: {updated}. Archivo: {csv_file}"
        ))
