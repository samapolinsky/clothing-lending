from django.urls import path, include

from . import views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    #path("", views.index, name="index"),
    path('', TemplateView.as_view(template_name="index.html")),
    path('accounts/', include('allauth.urls')),
    path('logout', LogoutView.as_view()),
	path("catalog/", views.catalog, name = "catalog"),
	path("checkout/", views.checkout, name = "checkout"),
]