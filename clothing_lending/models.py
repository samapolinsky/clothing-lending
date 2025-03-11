from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


# Create your models here.
class User(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'librarian'),
        (2, 'patron'),
    )
    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=2)


class Librarian(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Eventually add additional fields specific to librarians

    def __str__(self):
        return self.user.username


class Patron(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Eventually add additional fields specific to patrons

    def __str__(self):
        return self.user.username


class Collection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(Librarian, on_delete=models.CASCADE, related_name='collections')

    def __str__(self):
        return self.name


class Item(models.Model):
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    )
    
    SIZE_CHOICES = (
        ('XS', 'Extra Small'),
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
        ('XXXL', 'Triple Extra Large'),
        ('OS', 'One Size'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=100)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    image_url = models.URLField(blank=True)
    s3_image_key = models.CharField(max_length=255, blank=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='items')
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(Librarian, on_delete=models.CASCADE, related_name='items')

    def __str__(self):
        return self.name
