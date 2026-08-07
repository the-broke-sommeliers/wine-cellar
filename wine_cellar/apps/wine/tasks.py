import json
from datetime import timedelta

import pycountry
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.wine.emails import (
    send_drink_by_reminder,
    send_opened_bottle_reminder,
)
from wine_cellar.apps.wine.models import Category, Wine, WineType
from wine_cellar.apps.wine.serializers import WineAiSerializer
from wine_cellar.apps.wine.utils import (
    WINE_PREFILL_TIMEOUT,
    lat_long_to_geojson,
    match_choice_label,
    wine_prefill_cache,
)

AI_REQUEST_TIMEOUT = 60  # seconds
AI_REPROMPT_TIMEOUT = 20  # seconds

_wine_types = ", ".join([choice.label.lower() for choice in WineType])
_sweetness_categories = ", ".join([choice.label.lower() for choice in Category])

MODEL_INSTRUCTIONS = f"""
Return JSON with fields:
name: wine name
country: ISO2 code
type: {_wine_types}
size: float, bottle size in liters, e.g. 0.75, if no value guess
grapes: list of grapes
vintage: year
abs: float, alcohol %
sweetness: {_sweetness_categories}
vineyard: list of vineyard names
region: region
appellation: appellation
location: lat,long; if unknown use region or omit
"""


@shared_task(name="drink_by_reminder")
def drink_by_reminder():
    User = get_user_model()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(user_settings__notifications=False)
    )
    date = timezone.now().date() + timedelta(days=14)
    for user in users:
        wines = Wine.objects.filter(
            user=user, drink_by=date, storageitem__isnull=False
        ).distinct()
        if wines.count() > 0:
            send_drink_by_reminder(user, wines)


@shared_task(name="opened_bottle_reminder")
def opened_bottle_reminder():
    from wine_cellar.apps.storage.models import StorageItem

    User = get_user_model()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(user_settings__notifications=False)
    )
    today = timezone.now().date()
    for user in users:
        items = StorageItem.objects.filter(
            user=user, opened=True, deleted=False, drink_by=today
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


@shared_task(name="process_ai_wine_upload")
def process_ai_wine_upload(
    token, user_id, front=None, back=None, use_as_wine_images=False, barcode=None
):
    # See the comment in `_reprompt_field` - `litellm` import is deferred to
    # task runtime to keep it out of Django's module-loading path.
    import litellm.exceptions
    from litellm import completion

    content = [{"type": "text", "text": MODEL_INSTRUCTIONS}]
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
    except litellm.exceptions.AuthenticationError:
        _set_prefill_error(
            token,
            user_id,
            _(
                "AI request failed: invalid API key. Please check your "
                "configuration."
            ),
        )
        return
    except litellm.exceptions.RateLimitError:
        _set_prefill_error(
            token,
            user_id,
            _(
                "AI request failed: rate limit reached. "
                "Please wait a moment and try again."
            ),
        )
        return
    except (
        litellm.exceptions.ServiceUnavailableError,
        litellm.exceptions.BadGatewayError,
        litellm.exceptions.InternalServerError,
    ):
        _set_prefill_error(
            token,
            user_id,
            _(
                "AI service is temporarily unavailable. "
                "Please try again in a few minutes."
            ),
        )
        return
    except litellm.exceptions.Timeout:
        _set_prefill_error(token, user_id, _("AI request timed out. Please try again."))
        return
    except litellm.exceptions.APIConnectionError:
        _set_prefill_error(
            token,
            user_id,
            _(
                "Could not connect to the AI service. Please check your "
                "network and configuration."
            ),
        )
        return
    except litellm.exceptions.APIError:
        _set_prefill_error(
            token,
            user_id,
            _("AI request failed. Please try again or check your configuration."),
        )
        return

    ai_text = response.choices[0].message.content.strip()

    try:
        ai_json = _parse_ai_json(ai_text)
    except json.JSONDecodeError:
        _set_prefill_error(
            token,
            user_id,
            _(
                "Failed to process AI response. "
                "Please check the uploaded images and try again."
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
    if use_as_wine_images:
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
