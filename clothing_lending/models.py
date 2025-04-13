from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.utils import timezone


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
    custom_username = models.CharField(max_length=16, blank=True, null=True)
    profile_picture = models.CharField(max_length=255, blank=True, null=True)  # Store S3 URL
    s3_profile_picture_key = models.CharField(max_length=255, blank=True, null=True)  # Store S3 key

    def __str__(self):
        return self.custom_username if self.custom_username else self.user.username


class Collection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    is_private = models.BooleanField(default=False)
    allowed_patrons = models.ManyToManyField(Patron, blank=True, related_name='allowed_collections')

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
    image_url = models.TextField(blank=True)
    s3_image_key = models.CharField(max_length=255, blank=True)
    collections = models.ManyToManyField(Collection, related_name='items', blank=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(Librarian, on_delete=models.CASCADE, related_name='items')
    private_collection = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Lending(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('RETURNED', 'Returned')
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    borrower = models.ForeignKey(Patron, on_delete=models.CASCADE)
    request_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    approved_date = models.DateTimeField(null=True, blank=True)
    return_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.borrower} - {self.item.name} ({self.get_status_display()})"
    

# Modifying the Lending class to create a collection Invite model to add users to a private collection
class Invite(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ]
    
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    requester = models.ForeignKey(Patron, on_delete=models.CASCADE)
    request_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    approved_date = models.DateTimeField(null=True, blank=True)
    return_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.requester} - {self.collection.name} ({self.get_status_display()})"
