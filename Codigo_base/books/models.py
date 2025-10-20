from django.db import models
import numpy as np

def get_default_array():
    default_arr = np.random.rand(1536)
    return default_arr.astype(np.float32).tobytes()

class Book(models.Model):
    id = models.AutoField(primary_key=True)
    isbn = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=1024, db_column='Book-Title')
    authors = models.CharField(max_length=1024, blank=True, db_column='Book-Author')
    publication_date = models.CharField(max_length=20, blank=True, null=True, db_column='Year-Of-Publication')
    publisher = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True, db_column='Image-URL-M')
    average_rating = models.FloatField(null=True, blank=True, db_column='Average-Book-Rating')
    ratings_count = models.IntegerField(null=True, blank=True, db_column='Rating-Count')
    dominant_age_group = models.CharField(max_length=50, blank=True, null=True, db_column='Dominant-Age-Group')
    genre = models.CharField(max_length=100, blank=True, default="Sin género")
    description = models.TextField(blank=True, null=True)
    embeddings = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.title