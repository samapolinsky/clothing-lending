# filepath: c:\Users\kaden\CS3240\Lending\project-b-23\clothing_lending\signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import User, Librarian, Patron
from django.db.models.signals import m2m_changed
from .models import Item

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

@receiver(post_save, sender=User)
def create_or_update_patron(sender, instance, created, **kwargs):
    if instance.user_type == 2:
        Patron.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_patron(sender, instance, **kwargs):
    if instance.user_type == 2:
        try:
            instance.patron.save()
        except Patron.DoesNotExist:
            Patron.objects.create(user=instance)

@receiver(pre_save, sender=User)
def handle_user_type_change(sender, instance, **kwargs):
    if instance.pk:
        previous_user = User.objects.get(pk=instance.pk)
        if previous_user.user_type != instance.user_type:
            if previous_user.user_type == 1 and instance.user_type == 2:
                # User is being demoted from librarian to patron
                Librarian.objects.filter(user=instance).delete()
                Patron.objects.get_or_create(user=instance)
            elif previous_user.user_type == 2 and instance.user_type == 1:
                # User is being promoted from patron to librarian
                Patron.objects.filter(user=instance).delete()
                Librarian.objects.get_or_create(user=instance)

@receiver(m2m_changed, sender=Item.collections.through)
def update_item_privacy(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        # Check if we're dealing with an Item instance
        if hasattr(instance, 'collections'):
            # Instance is an Item, check if any of its collections are private
            has_private = instance.collections.filter(is_private=True).exists()
            instance.private_collection = has_private
            instance.save()
        # If instance is a Collection, we need to update all its items
        elif hasattr(instance, 'items'):
            for item in instance.items.all():
                # Check if any of the item's collections are private
                has_private = item.collections.filter(is_private=True).exists()
                item.private_collection = has_private
        instance.save()
