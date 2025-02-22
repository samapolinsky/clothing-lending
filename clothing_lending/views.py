from allauth.account.views import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.http import HttpResponse


# Create your views here.
def index(request):
	return HttpResponse("Hello world! If you're seeing this it means my Django and Heroku have been successfully linked.")

def catalog(request):
	return HttpResponse("This is the catalog of items.")

def checkout(request):
	return HttpResponse("I think this is a checkout idk if we need one.")

def is_librarian(user):
	return user.is_authenticated and user.user_type == 1

# @login_required
@user_passes_test(is_librarian)
def librarian_page(request):
	# need to change permissions so only librarians can access this page
	return render(request, 'librarian/page.html')

def is_patron(user):
	return user.is_authenticated and user.user_type == 2

# @login_required
@user_passes_test(is_patron)
def patron_page(request):
	return render(request, 'patron/page.html')


def logout_view(request):
	logout(request)
	# request.session.flush()
	return redirect('index.html')