from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Patron, Librarian, Collection, Item


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
    # Fields to display in the list view
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')

    # Add inlines based on user type
    def get_inline_instances(self, request, obj=None):
        if not obj:  # No object means we are in the "Add" view
            return []
        if obj.user_type == 1:  # Librarian
            return [LibrarianInline(self.model, self.admin_site)]
        elif obj.user_type == 2:  # Patron
            return [PatronInline(self.model, self.admin_site)]
        return []


# Inline for Items within Collection admin
class ItemInline(admin.TabularInline):
    model = Item
    extra = 0


# Register the custom UserAdmin
admin.site.register(User, UserAdmin)


# Register Collection and Item models
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'created_by')
    search_fields = ('name', 'description')
    inlines = [ItemInline]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'collection', 'size', 'condition', 'available')
    list_filter = ('collection', 'size', 'condition', 'available')
    search_fields = ('name', 'description', 'category')
