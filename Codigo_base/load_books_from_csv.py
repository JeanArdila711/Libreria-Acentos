import csv
from books.models import Book

# Ajusta la ruta si es necesario
csv_path = 'c:/Users/USUARIO/Downloads/archive/books.csv'

with open(csv_path, encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        Book.objects.create(
            title=row['title'],
            author=row['authors'],
            genre=row['genres'] if 'genres' in row else '',
            publication_year=int(row['original_publication_year']) if row['original_publication_year'] else None,
            cover_image=row['image_url'],
            synopsis=row['description'] if 'description' in row else '',
            price=None  # Puedes asignar un precio aleatorio o dejarlo en None
        )
print('Carga completada.')
