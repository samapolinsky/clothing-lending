from allauth.account.adapter import DefaultAccountAdapter


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
        user = request.user
        if user.user_type == 1:
            return '/lending/librarian/page/'
        elif user.user_type == 2:
            return '/lending/patron/page/'
        return super().get_login_redirect_url(request)

