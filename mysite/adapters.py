from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model


def determine_user_type(request):
    # need to implement this at some point
    pass


class CustomAccountAdapter(DefaultAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if not user.user_type:
            user.user_type = 2  # default to Patron
            user.save()

        return user

    def get_login_redirect_url(self, request):
        return '/lending/browse/'  # Redirect both librarians and patrons to the browse page


User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Check if the email is already registered
        email = sociallogin.account.extra_data.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
                # Link the social account to the existing user
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                user = User.objects.create_user(email=email, username=email)
                sociallogin.connect(request, user)