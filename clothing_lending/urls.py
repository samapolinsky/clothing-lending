from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView

# Import all views directly 
from .views import (
    # Basic views
    index, catalog, checkout, browse,
    
    # Authentication views
    logout_view,
    
    # Librarian views
    librarian_page, promote_user,
    
    # Patron views
    patron_page, update_patron_profile, remove_profile_picture,
    
    # Collection management
    add_collection, collection_detail, delete_collection, request_invite,
    
    # Item management
    add_item, item_detail, delete_item, request_borrow,
    
    # Lending management
    manage_lending_request,

    # Invite management
    manage_invite,
    
    # Debug & S3 helpers
    test_s3_connection, get_presigned_url, test_s3_upload, test_s3_permissions,
    
    # Test views
    test_view
)

urlpatterns = [
    # Basic routes
    path('', TemplateView.as_view(template_name="index.html")),
    path("catalog/", catalog, name="catalog"),
    path("checkout/", checkout, name="checkout"),
    path('browse/', browse, name='browse'),
    
    # Authentication routes
    path('accounts/', include('allauth.urls')),
    path('logout', LogoutView.as_view()),
    path('accounts/logout/', logout_view, name='logout'),
    
    # User dashboard routes
    path('librarian/page/', librarian_page, name='librarian_page'),
    path('patron/page/', patron_page, name='patron_page'),
    
    # Collection management routes
    path('collections/<uuid:collection_id>/', collection_detail, name='collection_detail'),
    path('collections/<uuid:collection_id>/delete/', delete_collection, name='delete_collection'),
    path('collections/<uuid:collection_id>/request-invite/', request_invite, name='request_invite'),
    path('librarian/collections/add/', add_collection, name='add_collection'),
    path('patron/collections/add/', add_collection, name='patron_add_collection'),  # Allow patrons to add collections
    
    # Item management routes
    path('librarian/items/add/', add_item, name='add_item'),
    path('items/<uuid:item_id>/', item_detail, name='item_detail'),
    path('items/<uuid:item_id>/delete/', delete_item, name='delete_item'),
    path('items/<uuid:item_id>/request-borrow/', request_borrow, name='request_borrow'),
    path('items/<uuid:item_id>/presigned-url/', get_presigned_url, name='get_presigned_url'),
    
    # Lending management routes
    path('lending/<int:lending_id>/manage/', manage_lending_request, name='manage_lending_request'),
    path('invite/<int:invite_id>/manage/', manage_invite, name='manage_invite'),
    
    # Librarian management routes
    path('librarian/promote/', promote_user, name='promote_user'),
    
    # Patron profile routes
    path('patron/update-profile/', update_patron_profile, name='update_patron_profile'),
    path('patron/remove-profile-picture/', remove_profile_picture, name='remove_profile_picture'),
    
    # Debug & testing routes
    path('test/', test_view, name='test_view'),
    path('test-borrow/<uuid:item_id>/', request_borrow, name='test_borrow'),
    path('test-s3/', test_s3_connection, name='test_s3_connection'),
    path('test-s3-upload/', test_s3_upload, name='test_s3_upload'),
    path('test-s3-permissions/', test_s3_permissions, name='test_s3_permissions'),
]
