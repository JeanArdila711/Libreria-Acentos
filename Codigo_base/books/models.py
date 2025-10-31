from django.db import models
import numpy as np
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


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
    precio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.title


# Modelo de Favoritos
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


# Modelo de Pedidos
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('shipped', 'Enviado'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=100, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipping_address = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Pedido #{self.order_number} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


# Items del pedido (detalle)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.book.title}"

    @property
    def subtotal(self):
        return self.quantity * self.price


# Modelo de Notificaciones/Preferencias de Usuario
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Preferencias de notificaciones
    email_notifications = models.BooleanField(default=True)
    newsletter = models.BooleanField(default=True)
    new_releases_alert = models.BooleanField(default=True)
    discount_alerts = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"


# 🆕 Modelo de Reseñas
class Review(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación de 1 a 5 estrellas"
    )
    comment = models.TextField(max_length=1000, help_text="Tu opinión sobre el libro")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    helpful_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('book', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.rating}⭐)"
