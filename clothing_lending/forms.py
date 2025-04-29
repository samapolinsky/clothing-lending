from django import forms
from .models import Collection, Item, Patron, Rating
from django.db.models import Q

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['name', 'description', 'is_private', 'allowed_patrons']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allowed_patrons': forms.SelectMultiple(attrs={'class': 'form-control'})
        }


class ItemForm(forms.ModelForm):
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    new_category = forms.CharField(required=False, label='New Category')
    
    class Meta:
        model = Item
        fields = ['name', 'description', 'categories', 'size', 'condition', 'available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'categories': forms.CheckboxSelectMultiple(),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categories'].required = False
    
    def clean_image(self):
        """
        Validate the image field.
        """
        image = self.cleaned_data.get('image')
        if image:
            # Print debug information
            print(f"Image file received: {image.name}, size: {image.size}, content type: {image.content_type}")
            
            # Check if the file is an image
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError("File is not an image")
                
            # Check file size (10MB limit)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Image file too large (> 10MB)")
                
        return image

class PromoteUserForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter user email'}))

class AddItemToCollectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.item = kwargs.pop('item', None)
        super(AddItemToCollectionForm, self).__init__(*args, **kwargs)
        if self.user and self.user.is_authenticated:
            if self.user.user_type == 1:  # Librarian
                self.fields['collections'].queryset = Collection.objects.all()
            elif self.user.user_type == 2:  # Patron
                self.fields['collections'].queryset = Collection.objects.filter(created_by=self.user)
        else:
            self.fields['collections'].queryset = Collection.objects.filter(is_private=False)


    collections = forms.ModelMultipleChoiceField(
        queryset=Collection.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        selected_collections = cleaned_data.get('collections')

        if self.item and selected_collections:
            current_collections = self.item.collections.all()
            current_is_private = current_collections.filter(is_private=True).exists()
            new_is_private = selected_collections.filter(is_private=True).exists()

            if new_is_private and current_collections.exists():
                raise forms.ValidationError(
                    f"Item '{self.item.name}' is already in a collection and cannot be added to a private one."
                )

            if current_is_private:
                raise forms.ValidationError(
                    f"Item '{self.item.name}' is in a private collection and cannot be added to others."
                )

# Make ANOTHER form to add to collection from the collections page
class AddItemToCollectionFromCollectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.collection = kwargs.pop('collection', None)
        super(AddItemToCollectionFromCollectionForm, self).__init__(*args, **kwargs)
        if self.collection.is_private:
            self.fields['items'].queryset = Item.objects.filter(collections__isnull=True)
        else:
            self.fields['items'].queryset = Item.objects.filter(Q(private_collection=False) & ~Q(collections=self.collection))


    items = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )

class PatronProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Patron
        fields = ['custom_username', 'profile_picture']
        widgets = {
            'custom_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your display name'}),
        }

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if image:
            #print("Test I am Printing the Image")
            #print(image)
            if isinstance(image, str): # if it returns an AWS S3 URL, i.e. no image file set
                return image # return the URL
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError("File is not an image")
            if image.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError("Image file too large (> 10MB)")
            return image

# and now I need to add a rating form argghhh
class RateItemForm(forms.ModelForm):
    num_rating = forms.IntegerField(
        required=True,
        min_value=1,
        max_value=5
    )

    #comment = forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Write a comment on the item'})

    class Meta:
        model = Rating
        fields = ['num_rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Write a comment on the item'}),
        }

    # now for an init i guess
    #def __init__(self, *args, **kwargs):
        #self.user = kwargs.pop('user', None)
        #self.item = kwargs.pop('item', None)
        #super(RateItemForm, self).__init__(*args, **kwargs)



