from django.urls import path, include

from . import views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from .views import librarian_page, logout_view, add_collection, add_item, item_detail, test_s3_connection, get_presigned_url, test_s3_upload, test_s3_permissions, promote_user, delete_item, collection_detail, delete_collection

urlpatterns = [
    # path("", views.index, name="index"),
    path('', TemplateView.as_view(template_name="index.html")),
    path('accounts/', include('allauth.urls')),
    path('logout', LogoutView.as_view()),
    path("catalog/", views.catalog, name="catalog"),
    path("checkout/", views.checkout, name="checkout"),
    path('librarian/page/', librarian_page, name='librarian_page'),
    # path('patron/page/', patron_page, name='patron_page'),
    path('accounts/logout/', logout_view, name='logout'),
    path('browse/', views.browse, name='browse'),
    
    # Collection management
    path('librarian/collections/add/', add_collection, name='add_collection'),
    path('collections/<uuid:collection_id>/', collection_detail, name='collection_detail'),
    path('collections/<uuid:collection_id>/delete/', delete_collection, name='delete_collection'),
    
    # Item management
    path('librarian/items/add/', add_item, name='add_item'),
    path('items/<uuid:item_id>/', item_detail, name='item_detail'),
    path('items/<uuid:item_id>/delete/', delete_item, name='delete_item'),
    
    # Debug & S3 helpers
    path('test-s3/', test_s3_connection, name='test_s3_connection'),
    path('test-s3-upload/', test_s3_upload, name='test_s3_upload'),
    path('test-s3-permissions/', test_s3_permissions, name='test_s3_permissions'),
    path('items/<uuid:item_id>/presigned-url/', get_presigned_url, name='get_presigned_url'),

    # Promote user to librarian
    path('librarian/promote/', promote_user, name='promote_user'),
]
