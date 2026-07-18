import base64
import json
import uuid
from decimal import Decimal

import litellm
import litellm.exceptions
from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.core.files.base import ContentFile
from django.db import IntegrityError, connections, transaction
from django.db.models import Avg, F, Q, Sum
from django.db.models.functions import Coalesce
from django.forms import model_to_dict
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, FormView, TemplateView
from django_filters.views import FilterView
from litellm import completion

from wine_cellar.apps.storage.models import StorageItem
from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.wine.fields import OpenChoiceModelFormViewMixin
from wine_cellar.apps.wine.filters import WineFilter
from wine_cellar.apps.wine.forms import (
    WineForm,
    WineUploadAIForm,
    image_fields_map,
)
from wine_cellar.apps.wine.models import (
    Category,
    Wine,
    WineImage,
    WineType,
)
from wine_cellar.apps.wine.serializers import WineAiSerializer


class HomePageView(TemplateView):
    template_name = "homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wines = Wine.objects.filter(user=self.request.user).count()
        wines_in_stock = (
            Wine.objects.filter(storageitem__isnull=False, storageitem__deleted=False)
            .filter(user=self.request.user)
            .distinct()
            .count()
        )
        bottles_in_stock = StorageItem.objects.filter(
            deleted=False, wine__user=self.request.user
        ).count()
        countries = (
            Wine.objects.filter(user=self.request.user)
            .values_list("country")
            .distinct()
            .count()
        )
        oldest = "-"
        youngest = "-"
        try:
            oldest = (
                Wine.objects.filter(user=self.request.user)
                .filter(vintage__isnull=False)
                .earliest("vintage")
                .vintage
            )
            youngest = (
                Wine.objects.filter(user=self.request.user)
                .filter(vintage__isnull=False)
                .latest("vintage")
                .vintage
            )
        except Wine.DoesNotExist:
            pass
        total_value = StorageItem.objects.aggregate(
            total=Sum(
                Coalesce("price", "wine__price"),
                filter=Q(deleted=False, wine__user=self.request.user),
            )
        )["total"] or Decimal("0")
        total_value = total_value.quantize(Decimal("0"))
        user_settings = get_user_settings(self.request.user)
        currency = settings.CURRENCY_SYMBOLS.get(
            getattr(user_settings, "currency", "EUR"), "€"
        )

        formatted_price = number_format(total_value, use_l10n=True)
        total_value = f"{formatted_price}{currency}"

        context.update(
            {
                "wines": wines,
                "wines_in_stock": wines_in_stock,
                "bottles_in_stock": bottles_in_stock,
                "countries": countries,
                "oldest": oldest,
                "youngest": youngest,
                "total_value": total_value,
            }
        )
        return context


class WineChooseActionView(TemplateView):
    template_name = "wine_choose_action.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ai_enabled = all(
            [getattr(settings, "AI_MODEL", None), getattr(settings, "AI_API_KEY", None)]
        )
        context.update({"ai_enabled": ai_enabled})
        if barcode := self.request.GET.get("barcode"):
            context.update({"barcode": barcode})
        return context


class WineBaseView(OpenChoiceModelFormViewMixin, FormView):
    form_class = WineForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("user", self.request.user)
        return kwargs

    def get_wine_instance(self):
        raise NotImplementedError

    def update_wine_from_cleaned_data(self, form, wine=None):
        cleaned_data = form.cleaned_data
        user = self.request.user

        self.create_new_objects(form)

        wine_fields = [
            "abv",
            "category",
            "barcode",
            "comment",
            "country",
            "name",
            "rating",
            "vintage",
            "drink_by",
            "wine_type",
            "price",
            "location",
        ]
        for field in wine_fields:
            setattr(wine, field, cleaned_data[field])
        wine.size = cleaned_data["size"][0]
        wine.region = cleaned_data["region"][0] if cleaned_data["region"] else None
        wine.appellation = (
            cleaned_data["appellation"][0] if cleaned_data["appellation"] else None
        )
        wine.user = user
        wine.save()

        for field in ["vineyard", "grapes", "food_pairings", "attributes", "source"]:
            getattr(wine, field).set(cleaned_data[field])

        for form_field, image_type in image_fields_map.items():
            image = cleaned_data.get(form_field)
            existing = WineImage.objects.filter(
                wine=wine, user=user, image_type=image_type
            )
            if image is False or (image and not hasattr(image, "instance")):
                if existing.exists():
                    old = existing.first()
                    old.image.delete()
                    old.thumbnail.delete()
                    existing.delete()
            if image and not hasattr(image, "instance"):
                WineImage.objects.get_or_create(
                    image=image, wine=wine, user=user, image_type=image_type
                )
        return wine


class WineCreateView(WineBaseView):
    template_name = "wine_create.html"
    success_url = reverse_lazy("wine-list")

    def get_initial(self):
        initial = super().get_initial()
        if barcode := self.request.GET.get("barcode"):
            initial["barcode"] = barcode
        if b64 := self.request.GET.get("ai_initial"):
            initial.update(WineAiSerializer().deserialize_ai_payload(b64))
        if token := self.request.GET.get("ai_images_token"):
            initial["ai_images_token"] = token
        return initial

    def get_wine_instance(self):
        return Wine()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.request.POST.get("ai_images_token") or self.request.GET.get(
            "ai_images_token"
        )
        context["ai_images_pending"] = bool(
            token and self.request.session.get(f"ai_images_{token}")
        )
        return context

    def _apply_ai_images(self, form, token):
        images = self.request.session.get(f"ai_images_{token}", {})
        field_map = {"front": "image_front", "back": "image_back"}
        for key, form_field in field_map.items():
            if form.cleaned_data.get(form_field):
                continue
            stashed = images.get(key)
            if not stashed:
                continue
            form.cleaned_data[form_field] = ContentFile(
                base64.b64decode(stashed["data"]), name=stashed["name"]
            )

    def form_valid(self, form):
        form_step = form.cleaned_data.get("form_step", 5)

        if form_step is None:
            form_step = 5
        if form_step == 5 or "save_finish" in self.request.POST:
            token = form.cleaned_data.get("ai_images_token")
            if token:
                self._apply_ai_images(form, token)
            try:
                with transaction.atomic():
                    self.update_wine_from_cleaned_data(
                        form=form, wine=self.get_wine_instance()
                    )
            except IntegrityError:
                form.add_error(
                    None, _("A wine with these details already exists in your cellar.")
                )
                return super().form_invalid(form)
            if token:
                self.request.session.pop(f"ai_images_{token}", None)
            return super().form_valid(form)
        elif form_step < 5:
            form.data = form.data.copy()
            if "back" in self.request.POST:
                form.data["form_step"] = max(0, form.cleaned_data["form_step"] - 1)
            else:
                form.data["form_step"] = form.cleaned_data["form_step"] + 1
            return super().form_invalid(form)
        return super().form_invalid(form)


class WineUpdateView(WineBaseView):
    template_name = "wine_edit.html"

    def get_initial(self):
        wine = get_object_or_404(Wine, pk=self.kwargs["pk"], user=self.request.user)
        return {**super().get_initial(), **model_to_dict(wine)}

    def get_wine_instance(self):
        return get_object_or_404(Wine, pk=self.kwargs["pk"], user=self.request.user)

    def form_valid(self, form):
        wine = self.get_wine_instance()
        try:
            with transaction.atomic():
                self.update_wine_from_cleaned_data(form=form, wine=wine)
        except IntegrityError:
            form.add_error(
                None, _("A wine with these details already exists in your cellar.")
            )
            return super().form_invalid(form)
        self.success_url = reverse_lazy("wine-detail", kwargs={"pk": wine.pk})
        return super().form_valid(form)


class WineDetailView(DetailView):
    template_name = "wine_detail.html"
    model = Wine

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class WineListView(FilterView):
    model = Wine
    template_name = "wine_list.html"
    context_object_name = "wines"
    filterset_class = WineFilter
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().order_by("-created")
        qs = qs.annotate(
            effective_price=Coalesce(
                Avg("storageitem__price"),
                F("price"),
            )
        )
        return qs.filter(user=self.request.user)


class WineScanView(TemplateView):
    template_name = "wine_scan.html"


class WineScannedView(TemplateView):
    template_name = "wine_scanned.html"

    def dispatch(self, request, *args, **kwargs):
        barcode = self.kwargs["barcode"]
        wine = (
            Wine.objects.filter(barcode=barcode).filter(user=self.request.user).first()
        )
        if wine:
            return redirect(reverse("wine-detail", kwargs={"pk": wine.pk}))

        return super().dispatch(request, *args, **kwargs)


class WineDeleteView(DeleteView):
    model = Wine
    template_name = "wine_confirm_delete.html"
    success_url = reverse_lazy("wine-list")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class WineMapView(TemplateView):
    template_name = "wine_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wines = Wine.objects.filter(user=self.request.user)

        context.update(
            {
                "wines": wines,
            }
        )
        return context


class WineUploadAIView(FormView):
    template_name = "wine_upload_ai.html"
    form_class = WineUploadAIForm
    success_url = reverse_lazy("wine-list")

    wine_types = ", ".join([choice.label.lower() for choice in WineType])
    sweetness_categories = ", ".join([choice.label.lower() for choice in Category])

    MODEL_INSTRUCTIONS = f"""
    Return JSON with fields:
    name: wine name
    country: ISO2 code
    type: {wine_types}
    size: float, bottle size in liters, e.g. 0.75, if no value guess
    grapes: list of grapes
    vintage: year
    abs: float, alcohol %
    sweetness: {sweetness_categories}
    vineyard: list of vineyard names
    region: region
    appellation: appellation
    location: lat,long; if unknown use region or omit
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ai_enabled = False
        if hasattr(settings, "AI_MODEL") and hasattr(settings, "AI_API_KEY"):
            if settings.AI_MODEL and settings.AI_API_KEY:
                ai_enabled = True
        context.update({"ai_enabled": ai_enabled})
        return context

    def form_valid(self, form):
        front_img = form.cleaned_data.get("front")
        back_img = form.cleaned_data.get("back")

        content = [{"type": "text", "text": self.MODEL_INSTRUCTIONS}]
        if front_img:
            front_b64 = base64.b64encode(front_img.read()).decode()
            front_url = (
                f"data:{front_img.content_type or 'image/jpeg'};base64,{front_b64}"
            )
            content.append({"type": "image_url", "image_url": {"url": front_url}})

        if back_img:
            back_b64 = base64.b64encode(back_img.read()).decode()
            back_url = f"data:{back_img.content_type or 'image/jpeg'};base64,{back_b64}"
            content.append({"type": "image_url", "image_url": {"url": back_url}})

        try:
            response = completion(
                model=settings.AI_MODEL,
                messages=[{"role": "user", "content": content}],
                api_key=settings.AI_API_KEY,
            )
        except litellm.exceptions.AuthenticationError:
            form.add_error(
                None,
                _(
                    "AI request failed: invalid API key. Please check your "
                    "configuration."
                ),
            )
            return self.form_invalid(form)
        except litellm.exceptions.RateLimitError:
            form.add_error(
                None,
                _(
                    "AI request failed: rate limit reached. "
                    "Please wait a moment and try again."
                ),
            )
            return self.form_invalid(form)
        except (
            litellm.exceptions.ServiceUnavailableError,
            litellm.exceptions.BadGatewayError,
            litellm.exceptions.InternalServerError,
        ):
            form.add_error(
                None,
                _(
                    "AI service is temporarily unavailable. "
                    "Please try again in a few minutes."
                ),
            )
            return self.form_invalid(form)
        except litellm.exceptions.Timeout:
            form.add_error(
                None,
                _("AI request timed out. Please try again."),
            )
            return self.form_invalid(form)
        except litellm.exceptions.APIConnectionError:
            form.add_error(
                None,
                _(
                    "Could not connect to the AI service. Please check your "
                    "network and configuration."
                ),
            )
            return self.form_invalid(form)
        except litellm.exceptions.APIError:
            form.add_error(
                None,
                _("AI request failed. Please try again or check your configuration."),
            )
            return self.form_invalid(form)
        ai_text = response.choices[0].message.content.strip()

        try:
            if ai_text.startswith("```"):
                ai_text = ai_text.split("```")[1]
            if ai_text.startswith("json"):
                ai_text = ai_text[4:]

            ai_json = json.loads(ai_text)
        except json.JSONDecodeError:
            form.add_error(
                None,
                _(
                    "Failed to process AI response. "
                    "Please check the uploaded images and try again."
                ),
            )
            return self.form_invalid(form)

        b64_initial = WineAiSerializer().serialize_ai_payload(ai_json)
        create_url = reverse("wine-add") + f"?ai_initial={b64_initial}"

        if form.cleaned_data.get("use_as_wine_images"):
            images = {}
            if front_img:
                images["front"] = {
                    "data": front_b64,
                    "name": front_img.name,
                    "content_type": front_img.content_type or "image/jpeg",
                }
            if back_img:
                images["back"] = {
                    "data": back_b64,
                    "name": back_img.name,
                    "content_type": back_img.content_type or "image/jpeg",
                }
            if images:
                token = uuid.uuid4().hex
                self.request.session[f"ai_images_{token}"] = images
                create_url += f"&ai_images_token={token}"

        if barcode := self.request.GET.get("barcode"):
            create_url += f"&barcode={barcode}"
        return redirect(create_url)


@login_not_required
def health_check(request):
    db_ok = all(conn.cursor().execute("SELECT 1") for conn in connections.all())
    status_code = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "unhealthy"}, status=status_code)
