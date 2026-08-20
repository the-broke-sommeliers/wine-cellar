from django.test import override_settings

from wine_cellar.apps.user.signup_adapter import ConfigurableSignupSocialAccountAdapter


def test_social_signup_open_by_default():
    adapter = ConfigurableSignupSocialAccountAdapter()
    assert adapter.is_open_for_signup(request=None, sociallogin=None) is True


@override_settings(ENABLE_SOCIAL_SIGNUPS=False)
def test_social_signup_closed_via_setting():
    adapter = ConfigurableSignupSocialAccountAdapter()
    assert adapter.is_open_for_signup(request=None, sociallogin=None) is False
