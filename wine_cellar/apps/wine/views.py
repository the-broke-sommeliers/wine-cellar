import base64
import uuid
from decimal import Decimal

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
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, View
from django_filters.views import FilterView

from wine_cellar.apps.storage.models import StorageItem
from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.wine.fields import OpenChoiceModelFormViewMixin
from wine_cellar.apps.wine.filters import WineFilter
from wine_cellar.apps.wine.forms import (
    WineForm,
    WineUploadAIForm,
    image_fields_map,
)
from wine_cellar.apps.wine.models import Wine, WineImage
from wine_cellar.apps.wine.serializers import WineAiSerializer
from wine_cellar.apps.wine.tasks import process_ai_wine_upload
from wine_cellar.apps.wine.utils import WINE_PREFILL_TIMEOUT, wine_prefill_cache


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
            token = uuid.uuid4().hex
            wine_prefill_cache.set(
                f"wine_prefill_{token}",
                {
                    "status": "done",
                    "initial": {"barcode": barcode},
                    "images": {},
                    "user_id": self.request.user.pk,
                },
                timeout=WINE_PREFILL_TIMEOUT,
            )
            context.update({"prefill_token": token})
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


class _PendingAiImage:
    """Placeholder ``initial`` value for an image stashed by the AI upload flow.

    It only exposes ``url`` (a data URI) so that ``NoFilenameClearableFileInput``
    renders its normal preview/clear-button UI for an image that hasn't actually
    been saved anywhere yet. It is never a real file - :meth:`WineCreateView.
    _apply_ai_images` swaps it out for the real, stashed ``ContentFile`` once the
    form is submitted.
    """

    def __init__(self, url):
        self.url = url


class WineCreateView(WineBaseView):
    template_name = "wine_create.html"
    success_url = reverse_lazy("wine-list")

    def get_initial(self):
        initial = super().get_initial()
        data = self._get_prefill_data()
        if data.get("initial"):
            initial.update(WineAiSerializer().deserialize_ai_payload(data["initial"]))
        if token := self._get_prefill_token():
            initial["prefill_token"] = token
        images = data.get("images", {})
        for key, form_field in {"front": "image_front", "back": "image_back"}.items():
            if stashed := images.get(key):
                initial[form_field] = _PendingAiImage(self._ai_image_data_url(stashed))
        return initial

    def get_wine_instance(self):
        return Wine()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        images = self._get_prefill_data().get("images", {})
        context["ai_images_pending"] = bool(images)
        context["ai_image_front_name"] = images.get("front", {}).get("name")
        context["ai_image_back_name"] = images.get("back", {}).get("name")
        return context

    def _get_prefill_token(self):
        return self.request.POST.get("prefill_token") or self.request.GET.get(
            "prefill_token"
        )

    def _get_prefill_data(self):
        data = _get_owned_prefill_entry(self._get_prefill_token(), self.request.user)
        if not data or data.get("status") != "done":
            # Missing, expired, belonging to a different user, or not yet
            # (or no longer) finished processing - all behave like no token.
            return {}
        return data

    @staticmethod
    def _ai_image_data_url(image):
        content_type = image.get("content_type") or "image/jpeg"
        return f"data:{content_type};base64,{image['data']}"

    def _apply_ai_images(self, form, images):
        field_map = {"front": "image_front", "back": "image_back"}
        for key, form_field in field_map.items():
            value = form.cleaned_data.get(form_field)
            # `False` means the user explicitly cleared it via the widget's clear
            # checkbox, and a real uploaded file means they replaced it - in both
            # cases the stashed AI image should not be applied.
            if value is False or (value and not isinstance(value, _PendingAiImage)):
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
            token = form.cleaned_data.get("prefill_token")
            prefill_data = self._get_prefill_data() if token else {}
            if prefill_data.get("images"):
                self._apply_ai_images(form, prefill_data["images"])
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
            if prefill_data:
                wine_prefill_cache.delete(f"wine_prefill_{token}")
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


def _get_owned_prefill_entry(token, user):
    if not token:
        return None
    data = wine_prefill_cache.get(f"wine_prefill_{token}")
    if not data or data.get("user_id") != user.pk:
        return None
    return data


class WineUploadAIView(FormView):
    template_name = "wine_upload_ai.html"
    form_class = WineUploadAIForm
    success_url = reverse_lazy("wine-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ai_enabled = False
        if hasattr(settings, "AI_MODEL") and hasattr(settings, "AI_API_KEY"):
            if settings.AI_MODEL and settings.AI_API_KEY:
                ai_enabled = True
        context.update({"ai_enabled": ai_enabled})
        return context

    @staticmethod
    def _encode_image(image):
        if not image:
            return None
        return {
            "data": base64.b64encode(image.read()).decode(),
            "name": image.name,
            "content_type": image.content_type or "image/jpeg",
        }

    def form_valid(self, form):
        front = self._encode_image(form.cleaned_data.get("front"))
        back = self._encode_image(form.cleaned_data.get("back"))

        token = uuid.uuid4().hex
        wine_prefill_cache.set(
            f"wine_prefill_{token}",
            {"status": "pending", "user_id": self.request.user.pk},
            timeout=WINE_PREFILL_TIMEOUT,
        )
        try:
            process_ai_wine_upload.delay(
                token=token,
                user_id=self.request.user.pk,
                front=front,
                back=back,
                use_as_wine_images=form.cleaned_data.get("use_as_wine_images"),
                barcode=self.request.GET.get("barcode"),
            )
        except Exception:
            wine_prefill_cache.delete(f"wine_prefill_{token}")
            form.add_error(
                None,
                _("Could not start the AI request. Please try again."),
            )
            return self.form_invalid(form)

        return redirect(reverse("wine-ai-upload-status", kwargs={"token": token}))


class WineUploadAIStatusView(TemplateView):
    template_name = "wine_upload_ai_status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs["token"]
        entry = _get_owned_prefill_entry(token, self.request.user)
        context["token"] = token
        context["poll_url"] = reverse("wine-ai-upload-poll", kwargs={"token": token})
        context["invalid"] = entry is None
        return context


class WineUploadAIPollView(View):
    def get(self, request, *args, **kwargs):
        entry = _get_owned_prefill_entry(self.kwargs["token"], request.user)
        if not entry:
            return JsonResponse(
                {
                    "status": "error",
                    "message": str(_("This AI request has expired.")),
                }
            )
        if entry.get("status") == "done":
            return JsonResponse(
                {
                    "status": "done",
                    "redirect": (
                        f"{reverse('wine-add')}?prefill_token={self.kwargs['token']}"
                    ),
                }
            )
        if entry.get("status") == "error":
            return JsonResponse(
                {"status": "error", "message": entry.get("message", "")}
            )
        return JsonResponse({"status": "pending", "stage": entry.get("stage")})


@login_not_required
def health_check(request):
    db_ok = all(conn.cursor().execute("SELECT 1") for conn in connections.all())
    status_code = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "unhealthy"}, status=status_code)
