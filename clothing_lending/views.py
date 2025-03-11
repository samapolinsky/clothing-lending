from allauth.account.views import logout
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages

from clothing_lending.models import User, Patron, Librarian, Collection, Item
from clothing_lending.forms import CollectionForm, ItemForm
from clothing_lending.s3_utils import upload_file_to_s3, get_s3_client, generate_presigned_url


# Create your views here.
def index(request):
	return HttpResponse("Hello world! If you're seeing this it means my Django and Heroku have been successfully linked.")

def catalog(request):
	return HttpResponse("This is the catalog of items.")

def checkout(request):
	return HttpResponse("I think this is a checkout idk if we need one.")

def is_librarian(user):
	return user.is_authenticated and user.user_type == 1

@user_passes_test(is_librarian)
def librarian_page(request):
	try:
		librarian = Librarian.objects.get(user=request.user)
		collections = Collection.objects.filter(created_by=librarian)
		recent_items = Item.objects.filter(created_by=librarian).order_by('-created_at')[:5]
		
		context = {
			'collections': collections,
			'recent_items': recent_items
		}
		
		return render(request, 'librarian/page.html', context)
	except Librarian.DoesNotExist:
		# Create librarian profile if it doesn't exist
		librarian = Librarian.objects.create(user=request.user)
		return render(request, 'librarian/page.html', {'collections': [], 'recent_items': []})

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
	"""
	View to browse all available items
	"""
	# Get all available items
	items = Item.objects.filter(available=True)
	
	# Get a list of all categories for filtering
	categories = Item.objects.values_list('category', flat=True).distinct()
	
	context = {
		'items': items,
		'categories': categories
	}
	
	return render(request, 'browse.html', context)


@user_passes_test(is_librarian)
def add_collection(request):
	if request.method == 'POST':
		form = CollectionForm(request.POST)
		if form.is_valid():
			collection = form.save(commit=False)
			librarian = Librarian.objects.get(user=request.user)
			collection.created_by = librarian
			collection.save()
			messages.success(request, 'Collection created successfully!')
			return redirect('librarian_page')
	else:
		form = CollectionForm()
	
	return render(request, 'librarian/add_collection.html', {'form': form})


@user_passes_test(is_librarian)
def add_item(request):
	if request.method == 'POST':
		form = ItemForm(request.POST, request.FILES)
		if form.is_valid():
			item = form.save(commit=False)
			librarian = Librarian.objects.get(user=request.user)
			item.created_by = librarian
			
			# Handle image upload to S3
			if 'image' in request.FILES:
				file_obj = request.FILES['image']
				s3_upload = upload_file_to_s3(file_obj)
				if s3_upload:
					item.image_url = s3_upload['url']
					item.s3_image_key = s3_upload['key']
			
			item.save()
			messages.success(request, 'Item created successfully!')
			return redirect('librarian_page')
	else:
		form = ItemForm()
	
	return render(request, 'librarian/add_item.html', {'form': form})


def item_detail(request, item_id):
	item = get_object_or_404(Item, pk=item_id)
	return render(request, 'item_detail.html', {'item': item})


def test_s3_connection(request):
    """
    A debug view to test S3 connection and image access.
    """
    try:
        # Get bucket info
        s3_client = get_s3_client()
        
        # List all buckets
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        
        # Check if our bucket exists
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        bucket_exists = bucket_name in buckets
        
        # List objects in our bucket (if it exists)
        bucket_objects = []
        if bucket_exists:
            try:
                objects = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
                if 'Contents' in objects:
                    bucket_objects = [
                        {
                            'key': obj['Key'], 
                            'url': f"https://{bucket_name}.s3.amazonaws.com/{obj['Key']}",
                            'last_modified': obj['LastModified'].isoformat(),
                            'size': obj['Size']
                        } 
                        for obj in objects['Contents']
                    ]
            except Exception as e:
                bucket_objects = [f"Error listing objects: {str(e)}"]
        
        # Check if any actual objects are in our bucket
        bucket_contents = len(bucket_objects) > 0
        
        return JsonResponse({
            'success': True,
            'buckets': buckets,
            'our_bucket': bucket_name,
            'bucket_exists': bucket_exists,
            'bucket_objects': bucket_objects,
            'bucket_has_contents': bucket_contents,
            'region': settings.AWS_S3_REGION_NAME
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def get_presigned_url(request, item_id):
    """
    Generate a fresh presigned URL for an item's image
    """
    try:
        item = get_object_or_404(Item, pk=item_id)
        
        if not item.s3_image_key:
            return JsonResponse({
                'success': False,
                'error': 'This item does not have an image'
            })
        
        # Generate a fresh presigned URL valid for 1 hour
        url = generate_presigned_url(item.s3_image_key, expiration=3600)
        
        if not url:
            return JsonResponse({
                'success': False,
                'error': 'Failed to generate presigned URL'
            })
        
        return JsonResponse({
            'success': True,
            'url': url,
            'key': item.s3_image_key,
            'expires': '1 hour'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })