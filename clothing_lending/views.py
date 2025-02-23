from allauth.account.views import logout
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.http import HttpResponse

from clothing_lending.models import User, Patron


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
	# Example items data - replace with database query later
	items = [
		{
			'name': 'Black Formal Suit',
			'category': 'Formal Wear',
			'size': 'M',
			'is_available': True,
			'image': {
				'url': 'https://example.com/suit.jpg'  # Replace with actual image URL
			}
		},
		{
			'name': 'Blue Business Dress',
			'category': 'Business',
			'size': 'S',
			'is_available': True,
			'image': {
				'url': 'https://example.com/dress.jpg'  # Replace with actual image URL
			}
		},
	]
	return render(request, 'patron/page.html', {'items': items})


def logout_view(request):
	logout(request)
	# request.session.flush()
	return redirect('index.html')

def get_google_user_info(request):
	# Check if the user is authenticated via Google
	if request.user.is_authenticated and request.user.social_auth.filter(provider='google-oauth2').exists():
		social_auth = request.user.social_auth.get(provider='google-oauth2')
		user_info = {
			'email': social_auth.extra_data.get('email'),
			'given_name': social_auth.extra_data.get('given_name'),
			'family_name': social_auth.extra_data.get('family_name'),
			'name': social_auth.extra_data.get('name'),
			'picture': social_auth.extra_data.get('picture'),
		}
		return user_info
	else:
		raise ValueError("User is not authenticated via Google OAuth.")

def google_oauth_callback(request):
	user_info = get_google_user_info(request)

	# Check if the user already exists
	try:
		user = User.objects.get(email=user_info['email'])
	except User.DoesNotExist:
		# Create a new user
		user = User.objects.create_user(
			username=user_info['email'],
			email=user_info['email'],
			first_name=user_info.get('given_name', ''),
			last_name=user_info.get('family_name', '')
		)

		# Create a Patron instance for the new user
		Patron.objects.create(user=user)

	# Log the user in
	login(request, user)

	return redirect('index.html')

def browse(request):
	# In the future, you'll want to fetch these from your database
	# This is just example data for now
	items = [
		{
			'name': 'Black Formal Suit',
			'category': 'Formal Wear',
			'size': 'M',
			'is_available': True,
			'image': {
				'url': 'https://example.com/suit.jpg'  # Replace with actual image URL
			}
		},
		# Add more items as needed
	]
	return render(request, 'browse.html', {'items': items})