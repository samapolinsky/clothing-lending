from django import forms
from .models import Collection, Item, Patron

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ItemForm(forms.ModelForm):
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Item
        fields = ['name', 'description', 'category', 'size', 'condition', 'available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'condition': forms.Select(attrs={'class': 'form-control'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
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
        user = kwargs.pop('user', None)
        super(AddItemToCollectionForm, self).__init__(*args, **kwargs)
        if user and user.is_authenticated:
            if user.user_type == 1:  # Librarian
                self.fields['collections'].queryset = Collection.objects.all()
            elif user.user_type == 2:  # Patron
                self.fields['collections'].queryset = Collection.objects.filter(created_by=user)
        else:
            self.fields['collections'].queryset = Collection.objects.filter(is_private=False)


    collections = forms.ModelMultipleChoiceField(
        queryset=Collection.objects.none(),
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
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError("File is not an image")
            if image.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError("Image file too large (> 10MB)")
        return image
