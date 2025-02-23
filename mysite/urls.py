"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from clothing_lending import views

def redirect_to_lending(request):
    return redirect("lending/")

urlpatterns = [
    # Forces empty path to also point to clothing_lending.urls
    # This works but if you add "/lending" to the end, then it shows the same exact page
	#path('', include('clothing_lending.urls')),
	path('', redirect_to_lending), # I think this change makes more sense
    # This redirects empty path to "/lending/" so that we go directly into the app I think
    path('admin/', admin.site.urls),
	path('lending/', include("clothing_lending.urls")),
	path('browse/', views.browse, name='browse'),
]
