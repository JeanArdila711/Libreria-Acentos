from django.db import models
import numpy as np

def get_default_array():
    default_arr = np.random.rand(1536)
    return default_arr.astype(np.float32).tobytes()

class Book(models.Model):
    publication_date = models.CharField(max_length=20, blank=True, null=True)
    id = models.AutoField(primary_key=True)
    book_id = models.IntegerField(null=True, blank=True, unique=True)
    num_pages = models.IntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=40, blank=True)
    isbn13 = models.CharField(max_length=40, blank=True)
    authors = models.CharField(max_length=1024, blank=True)
    title = models.CharField(max_length=1024)
    language_code = models.CharField(max_length=40, blank=True)
    average_rating = models.FloatField(null=True, blank=True)
    ratings_count = models.IntegerField(null=True, blank=True)
    text_reviews_count = models.IntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    genre = models.CharField(max_length=100, blank=True, default="Sin género")
    price = models.FloatField(null=True, blank=True)
    embeddings = models.JSONField(null=True, blank=True)


    def __str__(self):
        return self.title

    def __str__(self):
        return self.title