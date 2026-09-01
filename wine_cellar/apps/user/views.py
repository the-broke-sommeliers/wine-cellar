from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import UpdateView

from wine_cellar.apps.user.forms import UserSettingsForm
from wine_cellar.apps.user.models import UserSettings
from wine_cellar.apps.user.whats_new import (
    WHATS_NEW_CACHE_TIMEOUT,
    get_latest_whats_new_version,
    whats_new_cache,
    whats_new_cache_key,
)


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


class WhatsNewDismissView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        user_settings = get_user_settings(request.user)
        new_version = get_latest_whats_new_version()
        user_settings.last_seen_whats_new_version = new_version
        user_settings.save()

        whats_new_cache.set(
            whats_new_cache_key(request.user.pk),
            new_version,
            timeout=WHATS_NEW_CACHE_TIMEOUT,
        )

        next_url = request.POST.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("homepage")
