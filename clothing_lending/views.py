from allauth.account.views import logout
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
import uuid
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from clothing_lending.models import User, Patron, Librarian, Collection, Item, Lending, Invite, Category, Rating
from clothing_lending.forms import CollectionForm, ItemForm, PromoteUserForm, AddItemToCollectionForm, AddItemToCollectionFromCollectionForm, PatronProfileForm, RateItemForm
from clothing_lending.s3_utils import upload_file_to_s3, get_s3_client, generate_presigned_url, delete_file_from_s3


# Create your views here.
def index(request):
    return HttpResponse(
        "Hello world! If you're seeing this it means my Django and Heroku have been successfully linked.")


def catalog(request):
    return HttpResponse("This is the catalog of items.")


def checkout(request):
    return HttpResponse("I think this is a checkout idk if we need one.")


def is_librarian(user):
    return user.is_authenticated and user.user_type == 1


@user_passes_test(is_librarian)
def librarian_page(request):
    # Get the librarian instance for the current user
    librarian = get_object_or_404(Librarian, user=request.user)

    # Show only collections owned by this librarian
    collections = Collection.objects.filter(created_by=request.user)

    # Show only items created by this librarian
    recent_items = Item.objects.filter(created_by=librarian).order_by('-created_at')

    promote_form = PromoteUserForm()

    # Show only lending requests for items created by this librarian
    pending_requests = Lending.objects.filter(
        item__created_by=librarian,
        status='PENDING'
    ).order_by('-request_date')

    active_lendings = Lending.objects.filter(
        item__created_by=librarian,
        status='APPROVED',
        return_requested=False
    ).order_by('-approved_date')

    #print(active_lendings)

    # filter returns requested
    returns_requested = Lending.objects.filter(
        item__created_by=librarian,
        status='APPROVED',
        return_requested=True
    ).order_by('-approved_date')

    #print(returns_requested)

    # Finally, show pending invites!
    pending_invites = Invite.objects.filter(
        collection__created_by=request.user,
        status='PENDING'
    ).order_by('-request_date')

    context = {
        'collections': collections,
        'recent_items': recent_items,
        'form': promote_form,
        'pending_requests': pending_requests,
        'active_lendings': active_lendings,
        'returns_requested': returns_requested,
        'pending_invites': pending_invites
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
    query = request.GET.get('q')

    if request.user.is_authenticated and request.user.user_type == 1:
        collections = Collection.objects.all()

        if query:
            items = Item.objects.filter(
                Q(name__icontains=query) | Q(categories__name__icontains=query)
            ).distinct()
            collections = Collection.objects.filter(
                Q(name__icontains=query)
            ).distinct()
        else:
            items = Item.objects.all()
            collections = Collection.objects.all()

        restricted_collections = Collection.objects.none()

    elif request.user.is_authenticated and request.user.user_type == 2:
        try:
            patron = request.user.patron

            if query:
                items = Item.objects.filter(
                    Q(available=True) &
                    (Q(private_collection=False) | Q(collections__allowed_patrons=patron)) &
                    (Q(name__icontains=query) | Q(categories__name__icontains=query))
                ).distinct()
                collections = Collection.objects.filter(
                    (Q(is_private=False) | Q(allowed_patrons=patron)) &
                    Q(name__icontains=query))
            else:
                items = Item.objects.filter(
                    Q(available=True) &
                    (Q(private_collection=False) | Q(collections__allowed_patrons=patron))
                ).distinct()
                collections = Collection.objects.filter(Q(is_private=False) | Q(allowed_patrons=patron))
            restricted_collections = Collection.objects.exclude(Q(is_private=False) | Q(allowed_patrons=patron))

        except Patron.DoesNotExist:
            if query:
                items = Item.objects.filter(
                    Q(available=True) &
                    Q(private_collection=False) &
                    (Q(name__icontains=query) | Q(categories__name__icontains=query))
                ).distinct()
                collections = Collection.objects.filter(Q(is_private=False) & Q(name__icontains=query)).distinct()
            else:
                items = Item.objects.filter(
                    Q(available=True) &
                    Q(private_collection=False)
                ).distinct()
                collections = Collection.objects.filter(Q(is_private=False)).distinct()
            restricted_collections = Collection.objects.none()

    else:  # guest user
        if query:
            items = Item.objects.filter(
                Q(available=True) &
                Q(private_collection=False) &
                (Q(name__icontains=query) | Q(categories__name__icontains=query))
            ).distinct()
            collections = Collection.objects.filter(Q(is_private=False) & Q(name__icontains=query)).distinct()
        else:
            items = Item.objects.filter(
                Q(available=True) &
                Q(private_collection=False)
            ).distinct()
            collections = Collection.objects.filter(is_private=False)
        restricted_collections = Collection.objects.none()

    categories = Category.objects.all()

    context = {
        'items': items,
        'collections': collections,
        'restrictedcollections': restricted_collections,
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
            form.save_m2m()
            messages.success(request, 'Collection created successfully!')
            if request.user.user_type == 1:
                return redirect('librarian_page')
            elif request.user.user_type == 2:
                return redirect('patron_page')
    else:
        form = CollectionForm()

    patron = None
    if request.user.is_authenticated and request.user.user_type == 2:
        patron, created = Patron.objects.get_or_create(user=request.user)

    return render(request, 'librarian/add_collection.html', {
        'form': form,
        'librarians': Librarian.objects.all(),
        'patron': patron,
        })

def edit_collection(request, collection_id):
    user = request.user
    orig_collection = get_object_or_404(Collection, pk=collection_id)
    privacy_status = orig_collection.is_private
    collection = get_object_or_404(Collection, pk=collection_id)
    if request.method == 'POST':
        form = CollectionForm(request.POST, instance=orig_collection)
        if form.is_valid():
            #print(form)
            allowed_patrons = form.cleaned_data.get('allowed_patrons')
            print(allowed_patrons)
            collection = form.save(commit=False)
            collection.is_private = privacy_status
            collection.allowed_patrons.set(allowed_patrons)
            collection.created_by = orig_collection.created_by
            collection.created_at = orig_collection.created_at
            collection.save()
            print(collection.is_private)
            print(collection.allowed_patrons)
            form.save_m2m()
            messages.success(request, 'Collection updated successfully!')
            if request.user.user_type == 1:
                return redirect('librarian_page')
            elif request.user.user_type == 2:
                return redirect('patron_page')
    else:
        form = CollectionForm(instance=orig_collection)

    return render(request, 'edit_collection.html', {'form': form, 'user': user, 'collection': collection})


def user_can_view_collection(user, collection):
    if not collection.is_private:
        return True
    if user.user_type == 1:
        return True
    return user.patron in collection.allowed_patrons.all() # thanks to https://stackoverflow.com/questions/20931571/check-if-item-is-in-manytomany-field

# janky code to see if a user can view an item
def user_can_view_item(user, item):
    cv = True
    collections = item.collections.all()
    for collection in collections:
        if not user_can_view_collection(user, collection):
            cv = False
    return cv

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
                form.save_m2m()

                new_category_name = form.cleaned_data.get('new_category')
                if new_category_name:
                    new_cat, created = Category.objects.get_or_create(name=new_category_name)
                    item.categories.add(new_cat)  # Link it to this item
                    print(f"Added new category: {new_cat.name}")

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


# janky code to edit an item
@user_passes_test(is_librarian)
def edit_item(request, item_id):
    orig_item = get_object_or_404(Item, pk=item_id)
    item = get_object_or_404(Item, pk=item_id)
    if request.method == 'POST':
        form = ItemForm(request.POST or None, request.FILES or None, instance=item)
        print(f"Form submitted. Files in request: {request.FILES}")
        if form.is_valid():
            print("Form is valid")
            item = form.save(commit=False) # update item!
            # oh crud bug fix AAAA
            librarian = orig_item.created_by
            created_at = orig_item.created_at
            item.created_by = librarian
            item.created_at = created_at

            # Replace image upload to S3
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
                        # Delete old item picture from S3 if it exists
                        if item.s3_image_key:
                            from clothing_lending.s3_utils import delete_file_from_s3
                            delete_file_from_s3(item.s3_image_key)
                        # update item
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
                form.save_m2m()


                new_category_name = form.cleaned_data.get('new_category')
                if new_category_name:
                    new_cat, created = Category.objects.get_or_create(name=new_category_name)
                    item.categories.add(new_cat)  # Link new category
                    print(f"Added new category: {new_cat.name}")

                print(f"Item saved with ID: {item.id}")
                #print(f"Item image_url: {item.image_url}")
                #print(f"Item s3_image_key: {item.s3_image_key}")
                messages.success(request, 'Item edited successfully!')
                return redirect('librarian_page')
            except Exception as e:
                print(f"Error editing item: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"Error editing item: {str(e)}")
        else:
            print(f"Form errors: {form.errors}")
    else:
        form = ItemForm(instance=orig_item) # thanks to https://stackoverflow.com/questions/31406276/how-to-load-an-instance-in-django-modelforms
    # I am adding a comment as a test please deploy github pretty please please pleaseeee
    return render(request, 'edit_item.html', {'item': item, 'form': form})


def item_detail(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    # Get ratings
    ratings = Rating.objects.filter(item=item).order_by('-rate_date')
    avg = 0
    if ratings: # get average rating
        sum = 0
        for rating in ratings:
            sum = sum + rating.num_rating
        avg = round(sum / ratings.count(), 1)
    
    # Get patron for the current user if authenticated
    patron = None
    if request.user.is_authenticated and request.user.user_type == 2:
        patron, created = Patron.objects.get_or_create(user=request.user)
    
    if request.user.is_authenticated:
        can_view = user_can_view_item(request.user, item)
    else:
        can_view = True
        collections = item.collections.all()
        for collection in collections:
            if collection.is_private:
                can_view = False

    # check if you can review
    can_review = False
    if request.user.is_authenticated and request.user.user_type == 2:
        if not Rating.objects.filter(Q(item=item) & Q(rater=patron)).exists():
            can_review = True

    print(can_review)

    if request.method == 'POST' and 'add_to_collection' in request.POST:
        # form = AddItemToCollectionForm(request.POST, user=request.user if request.user.is_authenticated else None)
        form = AddItemToCollectionForm(request.POST, user=request.user if request.user.is_authenticated else None, item=item)

        if form.is_valid():
            collections = form.cleaned_data['collections']
            for collection in collections:
                item.collections.add(collection)
            messages.success(request, 'Item added to selected collections successfully.')
            return redirect('item_detail', item_id=item_id)
    else:
        # if request.user.is_authenticated:
        # form = AddItemToCollectionForm(user=request.user)
        form = AddItemToCollectionForm(
            user=request.user if request.user.is_authenticated else None,
            item=item
        )

    return render(request, 'item_detail.html', {'item': item, 'form': form, 'ratings': ratings, 'avg': avg, 'canview': can_view, 'patron': patron, 'canreview': can_review})

# stuff to rate an item yippeee
@user_passes_test(is_patron)
def rate_item(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    patron = request.user.patron
    if request.method == 'POST':
        form = RateItemForm(request.POST or None)
        print("Form submitted.")
        if form.is_valid():
            print("Form is valid")
            #numrating = form.cleaned_data['numrating']
            #comment = form.cleaned_data['comment']

            # Check if user already has rated this item
            existing_rating = Rating.objects.filter(
                item=item,
                rater=patron,
            ).exists()

            print(f"Existing rating check: {existing_rating}")  # Debug print

            if existing_rating:
                messages.warning(request, 'You cannot review the same item twice.')
                return redirect('item_detail', item_id=item_id)

            rating = form.save(commit=False) # make a rating!
            rating.rater = patron
            rating.item = item

            # Save the rating
            rating.save()
            form.save_m2m()
            messages.success(request, 'Your review has been added!')
            return redirect('item_detail', item_id=item_id)
        else:
            print(f"Form errors: {form.errors}")
    else:
        #print("I am loading a form")
        form = RateItemForm()
        #print(form)
    return render(request, 'rate_item.html', {'item': item, 'form': form})

@user_passes_test(is_patron)
def edit_rating(request, item_id):
    patron = request.user.patron
    item = get_object_or_404(Item, pk=item_id)
    if not Rating.objects.filter(Q(item=item) & Q(rater=patron)).exists():
        messages.warning(request, 'You cannot edit a review you have not posted.')
        return redirect('item_detail', item_id=item_id)
    rating = get_object_or_404(Rating, Q(item=item) & Q(rater=patron))
    orig_rate_date = rating.rate_date
    if request.method == 'POST':
        form = RateItemForm(request.POST or None, instance=rating)
        print("Form submitted.")
        if form.is_valid():
            print("Form is valid")
            #numrating = form.cleaned_data['numrating']
            #comment = form.cleaned_data['comment']

            # Check if user already has rated this item
            #existing_rating = Rating.objects.filter(
                #item=item,
                #rater=patron,
            #).exists()

            #print(f"Existing rating check: {existing_rating}")  # Debug print

            #if existing_rating:
                #messages.warning(request, 'You cannot review the same item twice.')
                #return redirect('item_detail', item_id=item_id)

            rating = form.save(commit=False) # make a rating!
            rating.rater = patron
            rating.item = item
            rating.rate_date = orig_rate_date # don't overwrite original rate date

            # Save the rating
            rating.save()
            form.save_m2m()
            messages.success(request, 'Your review has been updated!')
            return redirect('item_detail', item_id=item_id)
        else:
            print(f"Form errors: {form.errors}")
    else:
        #print("I am loading a form")
        form = RateItemForm(instance=rating)
        #print(form)
    return render(request, 'edit_rating.html', {'item': item, 'form': form})

# now to delete ratings
@user_passes_test(is_patron)
def delete_rating(request, item_id):
    item = get_object_or_404(Item, pk=item_id)
    patron = request.user.patron
    if not Rating.objects.filter(Q(item=item) & Q(rater=patron)).exists():
        messages.warning(request, 'You cannot delete a review you have not posted.')
        return redirect('item_detail', item_id=item_id)
    rating = get_object_or_404(Rating, Q(item=item) & Q(rater=patron))
    if request.method == 'POST':
        rating.delete()
        messages.success(request, 'Review deleted successfully!')
        return redirect('item_detail', item_id=item_id)

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
    if request.method == 'POST':
        # Delete item picture from S3 if it exists
        if item.s3_image_key:
            from clothing_lending.s3_utils import delete_file_from_s3
            delete_file_from_s3(item.s3_image_key)
        item.categories.clear()
        item.delete()
        messages.success(request, 'Item deleted successfully!')
        return redirect('librarian_page')


def collection_detail(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    items = collection.items.all()
    
    # Get patron for the current user if authenticated
    patron = None
    if request.user.is_authenticated and request.user.user_type == 2:
        patron, created = Patron.objects.get_or_create(user=request.user)
    
    if request.user.is_authenticated:
        can_view = user_can_view_collection(request.user, collection)
    else:
        if collection.is_private:
            can_view = False
        else:
            can_view = True
    
    # Get all librarians for display in private collections
    librarians = Librarian.objects.all()

    # Now let's have some other fun conditions
    can_add = False
    can_edit = False
    if request.user.is_authenticated:
        if request.user.user_type == 1:
            can_add = True
            can_edit = True
        else:
            if collection.created_by == request.user:
                can_add = True
                can_edit = True
    
        

    # Now let's have some other fun conditions
    can_add = False
    can_edit = False
    if request.user.is_authenticated:
        if request.user.user_type == 1:
            can_add = True
            can_edit = True
        else:
            if collection.created_by == request.user:
                can_add = True
                can_edit = True
    
        

    if request.method == 'POST' and 'add_to_collection' in request.POST:
        form = AddItemToCollectionFromCollectionForm(request.POST, user=request.user if request.user.is_authenticated else None, collection=collection)

        if form.is_valid():
            items = form.cleaned_data['items']
            for item in items:
                item.collections.add(collection)
            messages.success(request, 'Selected item(s) added to collection successfully.')
            return redirect('collection_detail', collection_id=collection_id)
    else:
        form = AddItemToCollectionFromCollectionForm(
            user=request.user if request.user.is_authenticated else None,
            collection=collection
        )

    # return render(request, 'collection_detail.html', {
    #     'collection': collection, 
    #     'items': items, 
    #     'canview': can_view, 
    #     "canadd": can_add, "canedit": can_edit, 'form': form,
    #     'librarians': librarians
    #     # 'patron': patron,
    # })

    context = {
        'collection': collection,
        'items': items,
        'canview': can_view,
        'canadd': can_add,
        'canedit': can_edit,
        'form': form,
        'librarians': librarians,
        'patron': patron,
    }
    
    return render(request, 'collection_detail.html', context)


@user_passes_test(is_librarian)
def delete_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    collection.delete()
    messages.success(request, 'Collection deleted successfully.')
    return redirect('librarian_page')


@user_passes_test(is_patron)
def patron_page(request):
    patron, created = Patron.objects.get_or_create(user=request.user)
    collections = Collection.objects.filter(Q(created_by=request.user) | Q(allowed_patrons=patron))  # Fetch collections created by the patron

    # Get all lending requests for this 
    pending_requests = Lending.objects.filter(
        borrower=patron,
        status='PENDING'
    ).order_by('-request_date')

    approved_items = Lending.objects.filter(
        borrower=patron,
        status='APPROVED'
    ).order_by('-approved_date')

    #print(approved_items)

    borrowing_history = Lending.objects.filter(
        borrower=patron,
        status__in=['RETURNED']
    ).order_by('-request_date')[:10]  # Show last 10 items

    rejected_requests = Lending.objects.filter(
        borrower=patron,
        status__in=['REJECTED']
    ).order_by('-request_date')[:10]  # Show last 10 items

    # Now get invites!
    pending_invites = Invite.objects.filter(
        requester=patron,
        status='PENDING'
    ).order_by('-request_date')

    # and reviews!
    my_ratings = Rating.objects.filter(
        rater=patron
    ).order_by('-rate_date')[:10]  # Show last 10 items rated

    context = {
        'collections': collections,
        'patron': patron,
        'pending_requests': pending_requests,
        'pending_invites': pending_invites,
        'approved_items': approved_items,
        'borrowing_history': borrowing_history,
        'rejected_requests': rejected_requests,
        'my_ratings': my_ratings
    }

    return render(request, 'patron/page.html', context)


def update_patron_profile(request):
    patron, created = Patron.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = PatronProfileForm(request.POST, request.FILES, instance=patron)
        print(f"Form submitted. Files in request: {request.FILES}")

        if form.is_valid():
            print("Form is valid")

            # Handle profile picture upload to S3
            if 'profile_picture' in request.FILES:
                file_obj = request.FILES['profile_picture']
                print(f"Profile picture found: {file_obj.name}")
                print(f"File size: {file_obj.size}")
                print(f"Content type: {file_obj.content_type}")

                try:
                    from clothing_lending.s3_utils import upload_file_to_s3
                    # Add more specific object name
                    object_name = f"profile_pics/{request.user.id}/{uuid.uuid4()}_{file_obj.name}"
                    print(f"Attempting to upload to S3 with object_name: {object_name}")

                    s3_upload = upload_file_to_s3(
                        file_obj,
                        object_name=object_name
                    )
                    print(f"S3 upload result: {s3_upload}")

                    if s3_upload:
                        # Delete old profile picture from S3 if it exists
                        if patron.s3_profile_picture_key:
                            from clothing_lending.s3_utils import delete_file_from_s3
                            delete_file_from_s3(patron.s3_profile_picture_key)

                        # Update patron with new S3 info
                        patron.profile_picture = s3_upload['url']
                        patron.s3_profile_picture_key = s3_upload['key']
                        patron.save()
                        print(f"Patron updated with new profile picture: {patron.profile_picture}")
                        messages.success(request, "Profile updated successfully!")
                    else:
                        print("S3 upload failed - returned None")
                        messages.error(request, "Failed to upload profile picture - S3 upload returned None")
                except Exception as e:
                    print(f"Error during upload: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    messages.error(request, f"Error uploading profile picture: {str(e)}")
            else:
                # Just save the form without picture changes
                form.save()
                messages.success(request, "Profile updated successfully!")
            return redirect('patron_page')
        else:
            print(f"Form errors: {form.errors}")
    else:
        form = PatronProfileForm(instance=patron)

    context = {'form': form, 'patron': patron}
    return render(request, 'patron/update_profile.html', context)


@user_passes_test(is_patron)
def remove_profile_picture(request):
    patron, created = Patron.objects.get_or_create(user=request.user)
    if patron.s3_profile_picture_key:
        # Delete the file from S3
        if delete_file_from_s3(patron.s3_profile_picture_key):
            patron.profile_picture = None
            patron.s3_profile_picture_key = None
            patron.save()
            messages.success(request, "Profile picture removed successfully.")
        else:
            messages.error(request, "Failed to remove profile picture.")
    else:
        messages.info(request, "No profile picture to remove.")
    return redirect('update_patron_profile')

@login_required
def request_borrow(request, item_id):
    print(f"request_borrow view called with item_id: {item_id}")  # Debug print

    if request.method == 'POST':
        print("POST request received")  # Debug print
        try:
            item = get_object_or_404(Item, pk=item_id)
            patron = get_object_or_404(Patron, user=request.user)

            print(f"Found item: {item.name} and patron: {patron}")  # Debug print

            # Check if item is available
            if not item.available:
                messages.error(request, 'This item is not available for borrowing.')
                return redirect(f'/lending/items/{item_id}/')

            # Check if user already has a pending or approved request for this item
            existing_request = Lending.objects.filter(
                item=item,
                borrower=patron,
                status__in=['PENDING', 'APPROVED']
            ).exists()

            print(f"Existing request check: {existing_request}")  # Debug print

            if existing_request:
                messages.warning(request, 'You already have a pending or approved request for this item.')
                return redirect(f'/lending/items/{item_id}/')

            # Create new lending request
            lending = Lending.objects.create(
                item=item,
                borrower=patron,
                status='PENDING',
                request_date=timezone.now()
            )

            print(f"Created new lending request: {lending.id}")  # Debug print

            # Update item availability
            item.available = False
            item.save()

            messages.success(request, 'Your borrow request has been submitted and is pending approval.')
            return redirect(f'/lending/items/{item_id}/')

        except Exception as e:
            print(f"Error in request_borrow: {str(e)}")  # Debug print
            import traceback
            traceback.print_exc()
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect(f'/lending/items/{item_id}/')

    return redirect(f'/lending/items/{item_id}/')

# alrighty, here's how to try inviting users to a private collection
@login_required
def request_invite(request, collection_id):
    print(f"request_invite view called with collection_id: {collection_id}")  # Debug print

    if request.method == 'POST':
        print("POST request received")  # Debug print
        try:
            collection = get_object_or_404(Collection, pk=collection_id)
            patron = get_object_or_404(Patron, user=request.user)

            print(f"Found collection: {collection.name} and patron: {patron}")  # Debug print

            # Check if item is available
            #if not item.available:
                #messages.error(request, 'This item is not available for borrowing.')
                #return redirect(f'/lending/items/{item_id}/')

            # Check if user already has a pending or approved request for this item
            existing_request = Invite.objects.filter(
                collection=collection,
                requester=patron,
                status__in=['PENDING', 'APPROVED']
            ).exists()

            print(f"Existing request check: {existing_request}")  # Debug print

            if existing_request:
                messages.warning(request, 'You already have a pending or approved request to view this collection.')
                return redirect(f'/lending/browse/')

            # Create new lending request
            invite = Invite.objects.create(
                collection=collection,
                requester=patron,
                status='PENDING',
                request_date=timezone.now()
            )

            print(f"Created new invite: {invite.id}")  # Debug print

            # Update item availability
            #item.available = False
            #item.save()

            messages.success(request, 'Your invite has been submitted and is pending approval.')
            return redirect(f'/lending/browse/')

        except Exception as e:
            print(f"Error in request_invite: {str(e)}")  # Debug print
            import traceback
            traceback.print_exc()
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect(f'/lending/browse/')

    return redirect(f'/lending/browse/')

@user_passes_test(is_patron)
def request_return(request, lending_id):
    lending = get_object_or_404(Lending, pk=lending_id)
    patron = get_object_or_404(Patron, user=request.user)

    # check if user borrowed item and lending is approved
    if lending.borrower == patron and lending.status == "APPROVED":
        lending.return_requested = True
        lending.save()
        messages.success(request, "Return requested successfully.")
        return redirect('/lending/patron/page/')
    else:
        messages.error(request, "You don't have permission to return this item.")
        return redirect('/lending/patron/page/')

@user_passes_test(is_librarian)
def manage_lending_request(request, lending_id):
    lending = get_object_or_404(Lending, pk=lending_id)
    librarian = get_object_or_404(Librarian, user=request.user)

    # Check if the current librarian is the creator of the item
    if lending.item.created_by != librarian:
        messages.error(request, "You don't have permission to manage this lending request. Only the librarian who created the item can approve or reject requests for it.")
        return redirect('/lending/librarian/page/')

    action = request.POST.get('action')

    if action == 'approve':
        lending.status = 'APPROVED'
        lending.approved_date = timezone.now()
        lending.due_date = timezone.now() + timedelta(days=14)
        messages.success(request, f'Lending request for {lending.item.name} has been approved.')
    elif action == 'reject':
        lending.status = 'REJECTED'
        lending.rejected_date = timezone.now()
        lending.item.available = True
        lending.item.save()
        messages.success(request, f'Lending request for {lending.item.name} has been rejected.')
    elif action == 'return':
        lending.status = 'RETURNED'
        lending.return_date = timezone.now()
        lending.item.available = True
        lending.item.save()
        messages.success(request, f'{lending.item.name} has been marked as returned.')

    lending.save()
    return redirect('/lending/librarian/page/')

# Now to approve patron invites to private collection
@user_passes_test(is_librarian)
def manage_invite(request, invite_id):
    invite = get_object_or_404(Invite, pk=invite_id)
    librarian = get_object_or_404(Librarian, user=request.user)

    # Check if the current librarian is the creator of the item
    if invite.collection.created_by.username != librarian.user.username:
        #print(invite.collection.created_by)
        #print(librarian)
        messages.error(request, "You don't have permission to invite. Only the librarian who created the collection can invite users.")
        return redirect('/lending/librarian/page/')

    action = request.POST.get('action')

    if action == 'approve':
        invite.status = 'APPROVED'
        invite.approved_date = timezone.now()
        invite.collection.allowed_patrons.add(invite.requester)
        invite.collection.save()
        messages.success(request, f'{invite.requester} invited to {invite.collection}.')
    elif action == 'reject':
        invite.status = 'REJECTED'
        messages.success(request, f'Invite by {invite.requester} to {invite.collection} has been rejected.')

    invite.save()
    return redirect('/lending/librarian/page/')

@login_required
def remove_item_from_collection(request, collection_id, item_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    item = get_object_or_404(Item, pk=item_id)
    
    # Check if the user has permission to modify this collection
    # Allow both the collection creator and any librarian
    if collection.created_by != request.user and request.user.user_type != 1:
        messages.error(request, "You don't have permission to modify this collection.")
        return redirect('collection_detail', collection_id=collection_id)
    
    # Remove the item from the collection
    # Use item.collections.remove() instead of collection.items.remove()
    # This ensures the signal receives an Item instance
    if collection in item.collections.all():
        item.collections.remove(collection)
        messages.success(request, f'"{item.name}" has been removed from the collection.')
    else:
        messages.warning(request, f'"{item.name}" is not in this collection.')
    
    return redirect('collection_detail', collection_id=collection_id)

@user_passes_test(is_librarian)
def remove_patron_access(request, collection_id, patron_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    patron = get_object_or_404(Patron, pk=patron_id)
    
    # Check if the user has permission to modify this collection
    if collection.created_by != request.user and request.user.user_type != 1:
        messages.error(request, "You don't have permission to modify this collection.")
        return redirect('collection_detail', collection_id=collection_id)
    
    # Remove the patron from the allowed_patrons list
    if patron in collection.allowed_patrons.all():
        collection.allowed_patrons.remove(patron)
        messages.success(request, f'Access for {patron.user.username} has been removed.')
    else:
        messages.warning(request, f'{patron.user.username} does not have access to this collection.')
    
    return redirect('collection_detail', collection_id=collection_id)

# Add a simple test view that always works
def test_view(request):
    return HttpResponse("This is a test view. If you see this, URL routing is working.")
