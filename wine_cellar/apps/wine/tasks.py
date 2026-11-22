import json
import logging
from datetime import timedelta

import pycountry
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import FETCH_RAISE, Q
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.wine.emails import (
    send_drink_by_reminder,
    send_opened_bottle_reminder,
)
from wine_cellar.apps.wine.models import (
    Category,
    FoodPairing,
    Vintage,
    Wine,
    WineType,
)
from wine_cellar.apps.wine.serializers import WineAiSerializer
from wine_cellar.apps.wine.utils import (
    WINE_PREFILL_TIMEOUT,
    ai_food_pairings_cache_key,
    ai_tasting_notes_cache_key,
    lat_long_to_geojson,
    match_choice_label,
    wine_prefill_cache,
)

logger = logging.getLogger(__name__)

AI_REQUEST_TIMEOUT = 60  # seconds
AI_REPROMPT_TIMEOUT = 20  # seconds
AI_UNEXPECTED_ERROR = _("The AI request failed. Please try again.")

_wine_types = ", ".join([choice.label.lower() for choice in WineType])
_sweetness_categories = ", ".join([choice.label.lower() for choice in Category])

BOTTLE_INTRO = """
You are shown one or two photos of a wine bottle - front and/or back label.
Examine both images closely, including any small or dense print on the back
label, and extract the following details.
"""

MENU_INTRO = """
You are shown a photo of a restaurant menu, wine list or price list. Entries
are short and often abbreviated (producer, appellation, vintage, price).
Choose ONE wine: {selection}
Expand abbreviations where you are confident (e.g. "Ch." -> "Château").
Ignore prices and section headings except as context (a heading like
"Rotweine" or "Champagne" implies the type). If no wine matches, return {{}}.
Otherwise extract the following details for the chosen wine.
"""

MENU_SELECTION_HINT = (
    'The user is looking for: "{hint}". Choose the entry that best matches it.'
)
MENU_SELECTION_DEFAULT = "the only wine listed, or else the most prominent one."

BOTTLE_SIZE = "float, bottle size in liters, e.g. 0.75, if no value guess"
MENU_SIZE = (
    "float, bottle size in liters if the menu gives one (e.g. 0.375, 0.75,\n"
    "  1.5); ignore glass pour sizes such as 0.1 or 0.15; if unclear use 0.75"
)

BOTTLE_VINTAGE = """four-digit harvest year as an integer, e.g. 2018. Look carefully
  at both label images for a year printed anywhere on the bottle, including
  large standalone numerals on the back label - it is not always next to
  the wine name. Only omit this field if no year appears anywhere."""
MENU_VINTAGE = """four-digit harvest year as an integer, e.g. 2018, as listed
  with the entry - menus often put it in its own column or after the name.
  Omit if no year is listed for the chosen wine."""

FIELD_SPEC = f"""
Return JSON only, with no surrounding commentary or markdown, containing
these fields. Unless a field's description below says otherwise, omit it
rather than guessing if it cannot be determined.

name: wine name
country: ISO2 code
type: {_wine_types}
size: {{size}}
grapes: list of grapes. If not printed, infer the likely grape(s) from the
  wine's type, region, and appellation when they strongly imply a variety
  (e.g. a red Burgundy is pinot noir, a Chablis is chardonnay, a Barolo is
  nebbiolo). Leave empty only if no variety can be reasonably inferred.
vintage: {{vintage}}
abs: float, alcohol %
sweetness: {_sweetness_categories}
vineyard: list of vineyard names
region: region
appellation: appellation
location: lat,long; if unknown use region or omit
"""


def build_model_instructions(source="bottle", hint=None):
    if source == "menu":
        hint = (hint or "").strip()
        selection = (
            MENU_SELECTION_HINT.format(hint=hint) if hint else MENU_SELECTION_DEFAULT
        )
        intro = MENU_INTRO.format(selection=selection)
        spec = FIELD_SPEC.format(size=MENU_SIZE, vintage=MENU_VINTAGE)
    else:
        intro = BOTTLE_INTRO
        spec = FIELD_SPEC.format(size=BOTTLE_SIZE, vintage=BOTTLE_VINTAGE)
    return intro + spec


@shared_task(name="drink_by_reminder")
def drink_by_reminder():
    User = get_user_model()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(user_settings__notifications=False)
    )
    date = timezone.localdate() + timedelta(days=14)
    for user in users:
        vintages = Vintage.objects.filter(
            wine__user=user, drink_by=date, storageitem__isnull=False
        ).distinct()
        if vintages.count() > 0:
            send_drink_by_reminder(user, vintages)


@shared_task(name="opened_bottle_reminder")
def opened_bottle_reminder():
    from wine_cellar.apps.storage.models import StorageItem

    User = get_user_model()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(user_settings__notifications=False)
    )
    today = timezone.localdate()
    for user in users:
        items = (
            StorageItem.objects.filter(
                user=user, opened=True, deleted=False, drink_by=today
            )
            .select_related("vintage__wine")
            .fetch_mode(FETCH_RAISE)
        )
        if items.exists():
            send_opened_bottle_reminder(user, items)


def _parse_ai_json(ai_text: str) -> dict:
    ai_text = ai_text.strip()
    if ai_text.startswith("```"):
        ai_text = ai_text.split("```")[1]
    if ai_text.startswith("json"):
        ai_text = ai_text[4:]
    return json.loads(ai_text)


def _reprompt_field(ai_json, field, ask):
    # `litellm` is a heavy import (~5s), so it's deferred to task runtime instead
    # of module load time - Django's URL system checks import this module on
    # every `manage.py` invocation via views.py, not just when the AI feature
    # actually runs.
    import litellm.exceptions
    from litellm import completion

    context = {
        f: ai_json[f]
        for f in ("name", "country", "region", "appellation", "vineyard", "vintage")
        if f != field and ai_json.get(f)
    }
    prompt = (
        f"{ask}\n"
        f"Wine details: {json.dumps(context)}\n"
        f'Return JSON with a single field, "{field}".'
    )
    try:
        response = completion(
            model=settings.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            api_key=settings.AI_API_KEY,
            timeout=AI_REPROMPT_TIMEOUT,
        )
        reprompt_json = _parse_ai_json(response.choices[0].message.content)
        return reprompt_json.get(field)
    except (
        litellm.exceptions.AuthenticationError,
        litellm.exceptions.RateLimitError,
        litellm.exceptions.ServiceUnavailableError,
        litellm.exceptions.BadGatewayError,
        litellm.exceptions.InternalServerError,
        litellm.exceptions.Timeout,
        litellm.exceptions.APIConnectionError,
        litellm.exceptions.APIError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        AttributeError,
        IndexError,
    ):
        logger.warning("AI reprompt for field %r failed", field, exc_info=True)
        return None


def _is_valid_location(value):
    try:
        lat_long_to_geojson(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_valid_country(value):
    return bool(pycountry.countries.get(alpha_2=value))


LOCATION_ASK = (
    "Based on this wine information, provide its approximate origin "
    'coordinates, formatted as "latitude,longitude" in decimal degrees '
    "using a plain ASCII hyphen-minus for negative values (e.g. "
    '"48.1374,-0.6603"). If coordinates cannot be determined, use null.'
)
COUNTRY_ASK = (
    "Based on this wine information, provide its country of origin as an "
    'ISO 3166-1 alpha-2 code (e.g. "FR", "DE", "US").'
)
TYPE_ASK = (
    "Based on this wine information, classify its type as exactly one of: "
    f"{_wine_types}."
)
SWEETNESS_ASK = (
    "Based on this wine information, classify its sweetness as exactly one "
    f"of: {_sweetness_categories}."
)


def _reprompt_and_fix(token, user_id, ai_json, field, ask, is_valid, stage):
    """If ai_json[field] is present but fails `is_valid`, ask the AI again
    for just that field and replace it with the corrected value - or drop
    it if the second attempt fails too. A missing field is left alone;
    re-asking with the same context it already had is unlikely to help."""
    value = ai_json.get(field)
    if not value or is_valid(value):
        return
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {"status": "pending", "stage": stage, "user_id": user_id},
        timeout=WINE_PREFILL_TIMEOUT,
    )
    new_value = _reprompt_field(ai_json, field, ask)
    ai_json[field] = new_value if new_value and is_valid(new_value) else None


def _image_data_url(image):
    return f"data:{image['content_type']};base64,{image['data']}"


def _set_prefill_error(token, user_id, message):
    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {"status": "error", "message": str(message), "user_id": user_id},
        timeout=WINE_PREFILL_TIMEOUT,
    )


def _ai_error_message(exc):
    """Log a litellm error and return its user message, else None."""
    import litellm.exceptions as e

    if isinstance(exc, e.AuthenticationError):
        logger.error("AI request failed: invalid API key")
        return _("AI request failed: invalid API key. Please check your configuration.")
    if isinstance(exc, e.RateLimitError):
        logger.warning("AI request failed: rate limit reached")
        return _(
            "AI request failed: rate limit reached. "
            "Please wait a moment and try again."
        )
    if isinstance(
        exc, (e.ServiceUnavailableError, e.BadGatewayError, e.InternalServerError)
    ):
        logger.exception("AI service is temporarily unavailable")
        return _(
            "AI service is temporarily unavailable. "
            "Please try again in a few minutes."
        )
    if isinstance(exc, e.Timeout):
        logger.warning("AI request timed out")
        return _("AI request timed out. Please try again.")
    if isinstance(exc, e.APIConnectionError):
        logger.exception("Could not connect to the AI service")
        return _(
            "Could not connect to the AI service. Please check your "
            "network and configuration."
        )
    if isinstance(exc, e.APIError):
        logger.exception("AI request failed")
        return _("AI request failed. Please try again or check your configuration.")
    return None


@shared_task(name="process_ai_wine_upload")
def process_ai_wine_upload(
    token,
    user_id,
    front=None,
    back=None,
    use_as_wine_images=False,
    barcode=None,
    source="bottle",
    hint=None,
):
    # See the comment in `_reprompt_field` - `litellm` import is deferred to
    # task runtime to keep it out of Django's module-loading path.
    from litellm import completion

    content = [{"type": "text", "text": build_model_instructions(source, hint)}]
    if front:
        content.append(
            {"type": "image_url", "image_url": {"url": _image_data_url(front)}}
        )
    if back:
        content.append(
            {"type": "image_url", "image_url": {"url": _image_data_url(back)}}
        )

    try:
        response = completion(
            model=settings.AI_MODEL,
            messages=[{"role": "user", "content": content}],
            api_key=settings.AI_API_KEY,
            timeout=AI_REQUEST_TIMEOUT,
        )
    except Exception as exc:
        message = _ai_error_message(exc)
        if message is None:
            raise
        _set_prefill_error(token, user_id, message)
        return

    ai_text = response.choices[0].message.content.strip()

    try:
        ai_json = _parse_ai_json(ai_text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse AI response as JSON", exc_info=True)
        _set_prefill_error(
            token,
            user_id,
            _(
                "Failed to process AI response. "
                "Please check the uploaded images and try again."
            ),
        )
        return

    if source == "menu" and not ai_json.get("name"):
        _set_prefill_error(
            token,
            user_id,
            _(
                "No matching wine found on the menu. "
                "Try a clearer photo or a more specific hint."
            ),
        )
        return

    _reprompt_and_fix(
        token,
        user_id,
        ai_json,
        "location",
        LOCATION_ASK,
        _is_valid_location,
        "location",
    )
    _reprompt_and_fix(
        token, user_id, ai_json, "country", COUNTRY_ASK, _is_valid_country, "country"
    )
    _reprompt_and_fix(
        token,
        user_id,
        ai_json,
        "type",
        TYPE_ASK,
        lambda v: match_choice_label(v, WineType.choices) is not None,
        "type",
    )
    _reprompt_and_fix(
        token,
        user_id,
        ai_json,
        "sweetness",
        SWEETNESS_ASK,
        lambda v: match_choice_label(v, Category.choices) is not None,
        "sweetness",
    )

    initial = WineAiSerializer().serialize_ai_payload(ai_json)
    if barcode:
        initial["barcode"] = barcode

    images = {}
    if use_as_wine_images and source != "menu":
        if front:
            images["front"] = front
        if back:
            images["back"] = back

    wine_prefill_cache.set(
        f"wine_prefill_{token}",
        {
            "status": "done",
            "initial": initial,
            "images": images,
            "user_id": user_id,
        },
        timeout=WINE_PREFILL_TIMEOUT,
    )


TASTING_NOTES_PROMPT = """
You are a sommelier. Based only on the wine details below, describe how this
wine is likely to look, smell and taste. You have not tasted it, so describe
its expected profile instead of reviewing it. Cover appearance, nose, palate
and finish, then suggest a serving temperature. Keep it to about 150 words of
plain text without markdown. Write in {language}.

Wine details:
{details}
"""

FOOD_PAIRINGS_PROMPT = """
You are a sommelier. Based on the wine details below, suggest 3 to 6 foods or
dishes that pair well with this wine. Use short names of 1 to 4 words, e.g.
"Roast lamb" or "Aged Comté".{existing} Write the names in {language}.
Return JSON only, with no surrounding commentary or markdown:
{{"food_pairings": ["...", "..."]}}

Wine details:
{details}
"""

FOOD_PAIRINGS_EXISTING = """
Where they fit, reuse these names from the user's collection, spelled exactly
as given: {names}."""

MAX_AI_FOOD_PAIRINGS = 8
MAX_EXISTING_FOOD_PAIRINGS = 200


def _language_name(user):
    language = get_user_settings(user).language
    try:
        return str(translation.get_language_info(language)["name"])
    except KeyError:
        return language


def _wine_details(wine, vintage=None):
    with translation.override("en"):
        details = {
            "Name": wine.name,
            "Type": wine.get_type,
            "Sweetness": wine.get_category,
            "Grapes": ", ".join(g.name for g in wine.grapes.all()),
            "Country": wine.country_name if wine.country else None,
            "Region": wine.region.name if wine.region else None,
            "Appellation": wine.appellation.name if wine.appellation else None,
            "Vineyards": ", ".join(v.name for v in wine.vineyard.all()),
        }
        if vintage:
            details["Vintage"] = vintage.year or "non-vintage"
            details["ABV"] = f"{vintage.abv}%" if vintage.abv else None
        return "\n".join(f"- {key}: {value}" for key, value in details.items() if value)


def build_tasting_notes_prompt(vintage):
    return TASTING_NOTES_PROMPT.format(
        language=_language_name(vintage.wine.user),
        details=_wine_details(vintage.wine, vintage),
    )


def build_food_pairings_prompt(wine, existing_names):
    existing = ""
    if existing_names:
        existing = FOOD_PAIRINGS_EXISTING.format(
            names=", ".join(f'"{name}"' for name in existing_names)
        )
    return FOOD_PAIRINGS_PROMPT.format(
        existing=existing,
        language=_language_name(wine.user),
        details=_wine_details(wine, wine.latest_vintage),
    )


def _is_current_ai_job(cache_key, job_id):
    # False once the user edited the target or started a newer job.
    entry = wine_prefill_cache.get(cache_key)
    return bool(entry) and entry.get("job_id") == job_id


def _set_ai_job_status(cache_key, user_id, job_id, status, message=None):
    if not _is_current_ai_job(cache_key, job_id):
        return
    entry = {"status": status, "user_id": user_id, "job_id": job_id}
    if message:
        entry["message"] = str(message)
    wine_prefill_cache.set(cache_key, entry, timeout=WINE_PREFILL_TIMEOUT)


def _run_ai_job(cache_key, user_id, job_id, func, *args):
    try:
        func(cache_key, user_id, job_id, *args)
    except Exception:
        _set_ai_job_status(cache_key, user_id, job_id, "error", AI_UNEXPECTED_ERROR)
        raise


def _ai_complete(prompt):
    """Return `(text, error_message)` for a single-prompt completion."""
    # See the comment in `_reprompt_field`.
    from litellm import completion

    try:
        response = completion(
            model=settings.AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            api_key=settings.AI_API_KEY,
            timeout=AI_REQUEST_TIMEOUT,
        )
    except Exception as exc:
        message = _ai_error_message(exc)
        if message is None:
            raise
        return None, message
    return (response.choices[0].message.content or "").strip(), None


@shared_task(name="generate_ai_tasting_notes")
def generate_ai_tasting_notes(vintage_id, user_id, job_id):
    _run_ai_job(
        ai_tasting_notes_cache_key(vintage_id),
        user_id,
        job_id,
        _generate_ai_tasting_notes,
        vintage_id,
    )


def _generate_ai_tasting_notes(cache_key, user_id, job_id, vintage_id):
    vintage = (
        Vintage.objects.filter(pk=vintage_id, wine__user_id=user_id)
        .select_related("wine__region", "wine__appellation", "wine__user")
        .first()
    )
    if not vintage:
        _set_ai_job_status(
            cache_key, user_id, job_id, "error", _("This vintage no longer exists.")
        )
        return

    text, error = _ai_complete(build_tasting_notes_prompt(vintage))
    if error:
        _set_ai_job_status(cache_key, user_id, job_id, "error", error)
        return
    if not text:
        _set_ai_job_status(
            cache_key,
            user_id,
            job_id,
            "error",
            _("The AI returned no tasting notes. Please try again."),
        )
        return
    if not _is_current_ai_job(cache_key, job_id):
        return
    vintage.ai_tasting_notes = text
    vintage.save(update_fields=["ai_tasting_notes"])
    _set_ai_job_status(cache_key, user_id, job_id, "done")


def _clean_food_pairing_names(value):
    if not isinstance(value, list):
        return []
    names = {}
    for item in value:
        if isinstance(item, str) and (name := item.strip()[:100]):
            names.setdefault(name.casefold(), name)
    return list(names.values())[:MAX_AI_FOOD_PAIRINGS]


def _get_or_create_food_pairing(available, name, user_id):
    pairing = available.filter(name__iexact=name).order_by("user_id").first()
    if pairing:
        return pairing
    try:
        with transaction.atomic():
            return FoodPairing.objects.create(name=name, user_id=user_id)
    except IntegrityError:
        return FoodPairing.objects.get(name=name, user_id=user_id)


@shared_task(name="generate_ai_food_pairings")
def generate_ai_food_pairings(wine_id, user_id, job_id):
    _run_ai_job(
        ai_food_pairings_cache_key(wine_id),
        user_id,
        job_id,
        _generate_ai_food_pairings,
        wine_id,
    )


def _generate_ai_food_pairings(cache_key, user_id, job_id, wine_id):
    wine = (
        Wine.objects.filter(pk=wine_id, user_id=user_id)
        .select_related("region", "appellation", "user")
        .first()
    )
    if not wine:
        _set_ai_job_status(
            cache_key, user_id, job_id, "error", _("This wine no longer exists.")
        )
        return

    available = FoodPairing.objects.filter(Q(user=None) | Q(user_id=user_id))
    existing_names = sorted(set(available.values_list("name", flat=True)))[
        :MAX_EXISTING_FOOD_PAIRINGS
    ]
    text, error = _ai_complete(build_food_pairings_prompt(wine, existing_names))
    if error:
        _set_ai_job_status(cache_key, user_id, job_id, "error", error)
        return

    try:
        names = _clean_food_pairing_names(_parse_ai_json(text).get("food_pairings"))
    except (json.JSONDecodeError, AttributeError, IndexError):
        logger.warning("Failed to parse AI food pairings response", exc_info=True)
        names = []
    if not names:
        _set_ai_job_status(
            cache_key,
            user_id,
            job_id,
            "error",
            _("The AI returned no food pairings. Please try again."),
        )
        return

    if not _is_current_ai_job(cache_key, job_id):
        return
    pairings = [_get_or_create_food_pairing(available, n, user_id) for n in names]
    wine.food_pairings.add(*pairings)
    _set_ai_job_status(cache_key, user_id, job_id, "done")
