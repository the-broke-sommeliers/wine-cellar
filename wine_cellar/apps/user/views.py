from django.conf import settings
from django.urls import reverse_lazy
from django.utils import translation
from django.views.generic import UpdateView

from wine_cellar.apps.user.forms import UserSettingsForm
from wine_cellar.apps.user.models import UserSettings


class UserSettingsView(UpdateView):
    template_name = "settings.html"
    form_class = UserSettingsForm
    success_url = reverse_lazy("user-settings")

    def form_valid(self, form):
        response = super().form_valid(form)
        user_language = form.cleaned_data["language"]
        translation.activate(user_language)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)
        return response

    def get_object(self, queryset=None):
        user = self.request.user
        return get_user_settings(user)


def get_user_settings(user):
    if not hasattr(user, "user_settings"):
        user.user_settings = UserSettings()
    return user.user_settings
