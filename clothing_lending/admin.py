from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Patron, Librarian, Collection, Item, Lending


# Inline for Librarian model
class LibrarianInline(admin.StackedInline):  # Use TabularInline for a table layout
    model = Librarian
    can_delete = False
    verbose_name_plural = 'Librarians'


# Inline for Patron model
class PatronInline(admin.StackedInline):
    model = Patron
    can_delete = False
    verbose_name_plural = 'Patrons'


# Custom UserAdmin
class UserAdmin(BaseUserAdmin):
    # Add user_type to the list of fields that can be edited
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    fieldsets = list(BaseUserAdmin.fieldsets) + [
        ('User Type', {'fields': ('user_type',)}),
    ]

# Make sure to register the custom UserAdmin
admin.site.register(User, UserAdmin)


# Register Collection and Item models
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_by', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_by', 'created_at', 'updated_at')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'size', 'condition', 'available', 'created_by', 'created_at', 'updated_at')
    list_filter = ('category', 'size', 'condition', 'available', 'created_by', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'category')
    filter_horizontal = ('collections',)  # Add this line to enable many-to-many field in admin

admin.site.register(Librarian)
admin.site.register(Patron)
admin.site.register(Lending)
