from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.utils import timezone
from django.core.validators import MaxValueValidator, MinValueValidator


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
    description = models.TextField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    is_private = models.BooleanField(default=False)
    allowed_patrons = models.ManyToManyField(Patron, blank=True, related_name='allowed_collections')

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

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
    categories = models.ManyToManyField(Category, related_name='items')
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
    due_date = models.DateTimeField(null=True, blank=True)
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
    #return_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.requester} - {self.collection.name} ({self.get_status_display()})"
    

# Making a class for ratings/comments
class Rating(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    rater = models.ForeignKey(Patron, on_delete=models.CASCADE)
    rate_date = models.DateTimeField(default=timezone.now)
    num_rating = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)]) #https://stackoverflow.com/questions/42425933/how-do-i-set-a-default-max-and-min-value-for-an-integerfield-django
    comment = models.TextField(max_length=200)
