from django.urls import path, include

from . import views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from .views import librarian_page, patron_page, logout_view

urlpatterns = [
    #path("", views.index, name="index"),
    path('', TemplateView.as_view(template_name="index.html")),
    path('accounts/', include('allauth.urls')),
    path('logout', LogoutView.as_view()),
	path("catalog/", views.catalog, name = "catalog"),
	path("checkout/", views.checkout, name = "checkout"),
    path('librarian/dashboard/', librarian_page, name='librarian_page'),
    path('patron/profile/', patron_page, name='patron_page'),
    path('accounts/logout/', logout_view, name='logout')

]