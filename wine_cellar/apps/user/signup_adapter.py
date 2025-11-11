from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class ConfigurableSignupAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        return getattr(settings, "ENABLE_SIGNUPS", False)
