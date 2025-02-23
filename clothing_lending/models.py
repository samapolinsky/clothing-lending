from django.contrib.auth.models import AbstractUser
from django.db import models


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
