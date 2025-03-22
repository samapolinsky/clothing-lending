# filepath: c:\Users\kaden\CS3240\Lending\project-b-23\clothing_lending\signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Librarian

@receiver(post_save, sender=User)
def create_or_update_librarian(sender, instance, created, **kwargs):
    if instance.user_type == 1:
        Librarian.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_librarian(sender, instance, **kwargs):
    if instance.user_type == 1:
        try:
            instance.librarian.save()
        except Librarian.DoesNotExist:
            Librarian.objects.create(user=instance)