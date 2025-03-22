from allauth.account.views import logout
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
import uuid

from clothing_lending.models import User, Patron, Librarian, Collection, Item
from clothing_lending.forms import CollectionForm, ItemForm, PromoteUserForm, AddItemToCollectionForm
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
    collections = Collection.objects.all()  # Fetch all collections
    recent_items = Item.objects.all().order_by('-created_at')  # Fetch all items
    promote_form = PromoteUserForm()  # Initialize the form

    context = {
        'collections': collections,
        'recent_items': recent_items,
        'form': promote_form  # Add the form to the context
    }

    return render(request, 'librarian/page.html', context)

def is_patron(user):
	return user.is_authenticated and user.user_type == 2

# # @login_required
# @user_passes_test(is_patron)
# def patron_page(request):
#     """
#     View for the patron dashboard
#     """
#     # Get all available items
#     items = Item.objects.filter(available=True)
    
#     # Get a list of all categories for filtering
#     categories = Item.objects.values_list('category', flat=True).distinct()
    
#     context = {
#         'items': items,
#         'categories': categories
#     }
    
#     return render(request, 'patron/page.html', context)


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
	
    # Get all collections
	collections = Collection.objects.all()
	
	# Get a list of all categories for filtering
	categories = Item.objects.values_list('category', flat=True).distinct()
	
	context = {
		'items': items,
		'collections': collections,
		'categories': categories
	}
	
	return render(request, 'browse.html', context)


def add_collection(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.created_by = request.user
            collection.save()
            messages.success(request, 'Collection created successfully!')
            if request.user.user_type == 1:
                return redirect('librarian_page')
            elif request.user.user_type == 2:
                return redirect('patron_page')
    else:
        form = CollectionForm()
    
    return render(request, 'librarian/add_collection.html', {'form': form})


@user_passes_test(is_librarian)
def add_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        print(f"Form submitted. Files in request: {request.FILES}")
        if form.is_valid():
            print("Form is valid")
            item = form.save(commit=False)
            librarian = Librarian.objects.get(user=request.user)
            item.created_by = librarian
            
            # Handle image upload to S3
            if 'image' in request.FILES:
                print(f"Image found in request.FILES: {request.FILES['image']}")
                file_obj = request.FILES['image']
                
                # Print file details
                print(f"File name: {file_obj.name}")
                print(f"File size: {file_obj.size}")
                print(f"File content type: {file_obj.content_type}")
                
                # Try to upload to S3
                try:
                    s3_upload = upload_file_to_s3(file_obj)
                    if s3_upload:
                        print(f"S3 upload successful: {s3_upload}")
                        item.image_url = s3_upload['url']
                        item.s3_image_key = s3_upload['key']
                    else:
                        print("S3 upload failed - returned None")
                        messages.error(request, "Failed to upload image to S3. Item saved without image.")
                except Exception as e:
                    print(f"Exception during S3 upload: {e}")
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f"Error uploading image: {str(e)}")
            else:
                print("No image in request.FILES")
            
            # Save the item
            try:
                item.save()
                print(f"Item saved with ID: {item.id}")
                print(f"Item image_url: {item.image_url}")
                print(f"Item s3_image_key: {item.s3_image_key}")
                messages.success(request, 'Item created successfully!')
                return redirect('librarian_page')
            except Exception as e:
                print(f"Error saving item: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"Error saving item: {str(e)}")
        else:
            print(f"Form errors: {form.errors}")
    else:
        form = ItemForm()
    
    return render(request, 'librarian/add_item.html', {'form': form})


def item_detail(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    if request.method == 'POST' and 'add_to_collection' in request.POST:
        form = AddItemToCollectionForm(request.POST, user=request.user)
        if form.is_valid():
            collections = form.cleaned_data['collections']
            for collection in collections:
                item.collections.add(collection)
            messages.success(request, 'Item added to selected collections successfully.')
            return redirect('item_detail', item_id=item_id)
    else:
        form = AddItemToCollectionForm(user=request.user)

    return render(request, 'item_detail.html', {'item': item, 'form': form})


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
        
        # Test bucket permissions
        bucket_permissions = test_bucket_permissions(bucket_name, s3_client)
        
        # List objects in our bucket (if it exists)
        bucket_objects = []
        if (bucket_exists):
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
            'bucket_permissions': bucket_permissions,
            'bucket_objects': bucket_objects,
            'bucket_has_contents': bucket_contents,
            'region': settings.AWS_S3_REGION_NAME
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def test_bucket_permissions(bucket_name, s3_client=None):
    """
    Test if we have the necessary permissions on the bucket.
    """
    if s3_client is None:
        s3_client = get_s3_client()
    
    results = {}
    
    # Test 1: Can we list objects?
    try:
        s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        results['list_objects'] = True
    except Exception as e:
        results['list_objects'] = False
        results['list_objects_error'] = str(e)
    
    # Test 2: Can we put a test object?
    test_key = f"test/permission_test_{uuid.uuid4()}.txt"
    try:
        # Use put_object instead of upload_fileobj
        test_content = b"This is a test file to check permissions"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        results['put_object'] = True
        
        # If we successfully uploaded, try to delete it
        try:
            s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            results['delete_object'] = True
        except Exception as e:
            results['delete_object'] = False
            results['delete_object_error'] = str(e)
            
    except Exception as e:
        results['put_object'] = False
        results['put_object_error'] = str(e)
    
    return results

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

def test_s3_upload(request):
    """
    A debug view to test S3 uploads directly.
    """
    if request.method == 'POST':
        if 'test_file' in request.FILES:
            file_obj = request.FILES['test_file']
            
            # Try to upload the file
            from clothing_lending.s3_utils import upload_file_to_s3
            result = upload_file_to_s3(file_obj)
            
            return JsonResponse({
                'success': result is not None,
                'upload_result': result,
                'file_info': {
                    'name': file_obj.name,
                    'size': file_obj.size,
                    'content_type': file_obj.content_type if hasattr(file_obj, 'content_type') else 'unknown'
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No file provided'
            })
    else:
        # Render a simple form for testing
        return render(request, 'test_s3_upload.html')

def test_s3_permissions(request):
    """
    A debug view to test S3 bucket permissions directly.
    """
    from django.conf import settings
    import boto3
    from io import BytesIO
    import uuid
    
    try:
        # Get S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Create a test file
        test_content = b"This is a test file to check S3 permissions"
        test_file = BytesIO(test_content)
        test_key = f"test/permission_test_{uuid.uuid4()}.txt"
        
        # Try to upload the file - removed ACL parameter
        response = s3_client.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        
        # Generate a presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': test_key
            },
            ExpiresIn=3600
        )
        
        # Standard URL
        standard_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{test_key}"
        
        # Try to delete the test file
        delete_response = s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=test_key
        )
        
        return JsonResponse({
            'success': True,
            'upload_response': str(response),
            'delete_response': str(delete_response),
            'presigned_url': presigned_url,
            'standard_url': standard_url,
            'test_key': test_key,
            'bucket': settings.AWS_STORAGE_BUCKET_NAME
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@user_passes_test(is_librarian)
def promote_user(request):
    if request.method == 'POST':
        form = PromoteUserForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                if user.user_type == 2:  # If the user is a patron
                    user.user_type = 1  # Promote to librarian
                    user.save()
                    # Create a Librarian instance if it doesn't exist
                    Librarian.objects.get_or_create(user=user)
                    # Delete the Patron instance if it exists
                    Patron.objects.filter(user=user).delete()
                    messages.success(request, f'{user.username} has been promoted to librarian.')
                else:
                    messages.info(request, f'{user.username} is already a librarian.')
            except User.DoesNotExist:
                messages.error(request, 'User with this email does not exist.')
        else:
            messages.error(request, 'Invalid email address.')
    return redirect('librarian_page')

@user_passes_test(is_librarian)
def delete_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    item.delete()
    messages.success(request, 'Item deleted successfully.')
    return redirect('librarian_page')

def collection_detail(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    items = collection.items.all()
    return render(request, 'collection_detail.html', {'collection': collection, 'items': items})

@user_passes_test(is_librarian)
def delete_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    collection.delete()
    messages.success(request, 'Collection deleted successfully.')
    return redirect('librarian_page')

@user_passes_test(is_patron)
def patron_page(request):
    collections = Collection.objects.filter(created_by=request.user)  # Fetch collections created by the patron

    context = {
        'collections': collections,
    }

    return render(request, 'patron/page.html', context)