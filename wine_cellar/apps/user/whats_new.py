import dataclasses

from django.core.cache import caches
from django.utils.translation import gettext_lazy as _

whats_new_cache = caches["whats_new"]
WHATS_NEW_CACHE_TIMEOUT = 60 * 60  # seconds; safety-net TTL for out-of-band DB writes


def whats_new_cache_key(user_id):
    return f"whats_new_last_seen_{user_id}"


@dataclasses.dataclass(frozen=True)
class WhatsNewRelease:
    version: str
    items: list


# Newest first. Append-only: never remove/reorder past entries - a user's
# stored last_seen_whats_new_version must always still be found in this list,
# otherwise get_unseen_releases() falls through and re-shows everything.
# Not every release needs an entry, only ones with user-facing highlights.
WHATS_NEW_RELEASES = [
    WhatsNewRelease(
        version="0.13.0",
        items=[
            _(
                "A wine can now have several vintages, so you no longer need "
                "a separate entry for every year. Your existing wines were "
                "automatically merged to fit the new setup. Let us know what "
                "you think of the new design."
            ),
            _('Added a "What\'s New" screen to highlight notable changes.'),
        ],
    ),
]


def get_unseen_releases(last_seen_version):
    known_versions = {release.version for release in WHATS_NEW_RELEASES}
    if last_seen_version and last_seen_version not in known_versions:
        # Unrecognized version (e.g. a past release entry was later removed,
        # violating the append-only convention). Fail safe: don't resurface
        # every release, just show nothing new.
        return []

    unseen = []
    for release in WHATS_NEW_RELEASES:
        if release.version == last_seen_version:
            break
        unseen.append(release)
    return unseen


def get_latest_whats_new_version():
    return WHATS_NEW_RELEASES[0].version if WHATS_NEW_RELEASES else ""
