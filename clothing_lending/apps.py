from django.apps import AppConfig


class ClothingLendingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clothing_lending'

    def ready(self):
        import clothing_lending.signals