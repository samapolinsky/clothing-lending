from allauth.account.views import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse


# Create your views here.
def index(request):
	return HttpResponse("Hello world! If you're seeing this it means my Django and Heroku have been successfully linked.")

def catalog(request):
	return HttpResponse("This is the catalog of items.")

def checkout(request):
	return HttpResponse("I think this is a checkout idk if we need one.")

@login_required
def librarian_page(request):
	return render(request, 'librarian/page.html')


@login_required
def patron_page(request):
	return render(request, 'patron/page.html')


def logout_view(request):
	logout(request)
	# request.session.flush()
	return redirect('index.html')