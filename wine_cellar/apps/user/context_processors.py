from django.conf import settings

from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.user.whats_new import (
    WHATS_NEW_CACHE_TIMEOUT,
    get_unseen_releases,
    whats_new_cache,
    whats_new_cache_key,
)


def whats_new(request):
    if not getattr(settings, "ENABLE_WHATS_NEW", True):
        return {}
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    cache_key = whats_new_cache_key(user.pk)
    last_seen_version = whats_new_cache.get(cache_key)
    if last_seen_version is None:
        last_seen_version = get_user_settings(user).last_seen_whats_new_version
        whats_new_cache.set(
            cache_key, last_seen_version, timeout=WHATS_NEW_CACHE_TIMEOUT
        )

    return {"whats_new_releases": get_unseen_releases(last_seen_version)}
