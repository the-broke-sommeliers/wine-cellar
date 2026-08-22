import base64
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.core.files.base import ContentFile
from django.db import IntegrityError, connections, transaction
from django.db.models import (
    Avg,
    Count,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
)
from django.db.models.functions import Coalesce
from django.forms import model_to_dict
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.formats import number_format
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, View
from django_filters.views import FilterView

from wine_cellar.apps.storage.models import (
    StorageItem,
    StorageItemEvent,
    StorageItemEventType,
)
from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.wine.fields import OpenChoiceModelFormViewMixin
from wine_cellar.apps.wine.filters import WineFilter
from wine_cellar.apps.wine.forms import (
    VintageForm,
    WineForm,
    WineUploadAIForm,
    image_fields_map,
)
from wine_cellar.apps.wine.models import ImageType, Vintage, Wine, WineImage
from wine_cellar.apps.wine.serializers import WineAiSerializer
from wine_cellar.apps.wine.tasks import process_ai_wine_upload
from wine_cellar.apps.wine.utils import WINE_PREFILL_TIMEOUT, wine_prefill_cache


class HomePageView(TemplateView):
    template_name = "homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wines = Wine.objects.filter(user=self.request.user).count()
        wines_in_stock = (
            Wine.objects.filter(
                vintages__storageitem__isnull=False,
                vintages__storageitem__deleted=False,
            )
            .filter(user=self.request.user)
            .distinct()
            .count()
        )
        bottles_in_stock = StorageItem.objects.filter(
            deleted=False, vintage__wine__user=self.request.user
        ).count()
        countries = (
            Wine.objects.filter(user=self.request.user)
            .values_list("country")
            .distinct()
            .count()
        )
        oldest = (
            Vintage.objects.filter(wine__user=self.request.user, year__isnull=False)
            .order_by("year")
            .values_list("year", flat=True)
            .first()
        ) or "-"
        youngest = (
            Vintage.objects.filter(wine__user=self.request.user, year__isnull=False)
            .order_by("-year")
            .values_list("year", flat=True)
            .first()
        ) or "-"
        total_value = StorageItem.objects.aggregate(
            total=Sum(
                Coalesce("price", "vintage__price"),
                filter=Q(deleted=False, vintage__wine__user=self.request.user),
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


WINE_FIELDS = ["category", "country", "name", "wine_type", "location"]
VINTAGE_FIELDS = ["abv", "barcode", "comment", "year", "drink_by", "price", "rating"]


def latest_vintage_prefetch():
    """Prefetch each wine's vintages (newest first) with their front image,
    so wine.latest_vintage/.image_thumbnail resolve with no extra queries."""
    return Prefetch(
        "vintages",
        queryset=Vintage.objects.order_by("-year").prefetch_related(
            Prefetch(
                "wineimage_set",
                queryset=WineImage.objects.filter(image_type=ImageType.FRONT),
                to_attr="_prefetched_front_images",
            )
        ),
        to_attr="_prefetched_vintages",
    )


class _DuplicateVintageYearError(IntegrityError):
    """Raised in place of a plain IntegrityError when the collision on
    saving a wine's vintage is specifically the (wine, year, user) unique
    constraint, so callers can show a vintage-specific message instead of
    the wine-level "already exists" one."""


class WineBaseView(OpenChoiceModelFormViewMixin, FormView):
    form_class = WineForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("user", self.request.user)
        return kwargs

    def get_wine_instance(self):
        raise NotImplementedError

    def get_vintage_instance(self, wine):
        raise NotImplementedError

    def update_wine_from_cleaned_data(self, form, wine=None):
        cleaned_data = form.cleaned_data
        user = self.request.user

        self.create_new_objects(form)

        for field in WINE_FIELDS:
            setattr(wine, field, cleaned_data[field])
        wine.size = cleaned_data["size"][0]
        wine.region = cleaned_data["region"][0] if cleaned_data["region"] else None
        wine.appellation = (
            cleaned_data["appellation"][0] if cleaned_data["appellation"] else None
        )
        wine.user = user
        is_new = wine.pk is None
        wine.save()

        for field in ["vineyard", "grapes", "food_pairings", "attributes", "source"]:
            related_manager = getattr(wine, field)
            if is_new:
                # A brand-new wine has no existing relations yet, so .set()'s
                # mandatory "fetch old ids" diff query would always come back
                # empty - add() skips that query entirely.
                if cleaned_data[field]:
                    related_manager.add(*cleaned_data[field])
            else:
                related_manager.set(cleaned_data[field])

        vintage = self.get_vintage_instance(wine)
        for field in VINTAGE_FIELDS:
            setattr(vintage, field, cleaned_data.get(field))
        vintage.user = user
        try:
            vintage.save()
        except IntegrityError as exc:
            raise _DuplicateVintageYearError from exc

        for form_field, image_type in image_fields_map.items():
            image = cleaned_data.get(form_field)
            if image is False or (image and not hasattr(image, "instance")):
                old = WineImage.objects.filter(
                    vintage=vintage, user=user, image_type=image_type
                ).first()
                if old:
                    # save=False: the row is deleted right below anyway, so
                    # the model re-save that save=True would trigger is waste.
                    old.image.delete(save=False)
                    old.thumbnail.delete(save=False)
                    old.delete()
            if image and not hasattr(image, "instance"):
                WineImage.objects.get_or_create(
                    image=image, vintage=vintage, user=user, image_type=image_type
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

    def get_vintage_instance(self, wine):
        return Vintage(wine=wine)

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
                    wine = self.update_wine_from_cleaned_data(
                        form=form, wine=self.get_wine_instance()
                    )
                    StorageItemEvent.objects.create(
                        wine=wine,
                        wine_name=wine.name,
                        user=self.request.user,
                        event_type=StorageItemEventType.WINE_ADDED,
                    )
            except _DuplicateVintageYearError:
                form.add_error(
                    "year", _("A vintage with this year already exists for this wine.")
                )
                return super().form_invalid(form)
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
        self._wine = get_object_or_404(
            Wine, pk=self.kwargs["pk"], user=self.request.user
        )
        initial = {**super().get_initial(), **model_to_dict(self._wine)}
        vintage = self._wine.latest_vintage
        if vintage:
            initial["vintage_id"] = vintage.pk
            for field in VINTAGE_FIELDS:
                initial[field] = getattr(vintage, field)
        return initial

    def get_wine_instance(self):
        # get_initial() runs earlier in the same request (get_form_kwargs()
        # always calls it) and already fetched this exact row.
        if not hasattr(self, "_wine"):
            self._wine = get_object_or_404(
                Wine, pk=self.kwargs["pk"], user=self.request.user
            )
        return self._wine

    def get_vintage_instance(self, wine):
        return wine.latest_vintage or Vintage(wine=wine)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wine"] = self.get_wine_instance()
        return context

    def form_valid(self, form):
        wine = self.get_wine_instance()
        try:
            with transaction.atomic():
                self.update_wine_from_cleaned_data(form=form, wine=wine)
        except _DuplicateVintageYearError:
            form.add_error(
                "year", _("A vintage with this year already exists for this wine.")
            )
            return super().form_invalid(form)
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
        qs = (
            super()
            .get_queryset()
            .select_related(
                "region", "appellation", "size", "user", "user__user_settings"
            )
        )
        return qs.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vintages"] = self.object.vintages.order_by("-year").prefetch_related(
            Prefetch(
                "wineimage_set",
                queryset=WineImage.objects.filter(image_type=ImageType.FRONT),
                to_attr="_prefetched_front_images",
            )
        )
        return context


class WineListView(FilterView):
    model = Wine
    template_name = "wine_list.html"
    context_object_name = "wines"
    filterset_class = WineFilter
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().order_by("-created")
        # effective_price's two Avg()s each average a different relation
        # (storageitem vs. vintages directly) - combined into one annotate()
        # they'd share the "vintages" join with total_stock_count's Count(),
        # multiplying rows before aggregating (Django's classic "multiple
        # aggregations across multi-valued relations" fan-out) and skewing
        # every one of them for a wine with more than one vintage and/or
        # more than one stock item. Correlated subqueries can't fan out
        # into each other or into the Count() below, so each average stays
        # correct in isolation.
        storage_avg_price = (
            StorageItem.objects.filter(vintage__wine=OuterRef("pk"))
            .order_by()
            .values("vintage__wine")
            .annotate(avg_price=Avg("price"))
            .values("avg_price")
        )
        vintage_avg_price = (
            Vintage.objects.filter(wine=OuterRef("pk"))
            .order_by()
            .values("wine")
            .annotate(avg_price=Avg("price"))
            .values("avg_price")
        )
        qs = qs.annotate(
            effective_price=Coalesce(
                Subquery(storage_avg_price),
                Subquery(vintage_avg_price),
            ),
            total_stock_count=Count(
                "vintages__storageitem",
                filter=Q(vintages__storageitem__deleted=False),
                distinct=True,
            ),
            # Max/Min are unaffected by join fan-out (repeating a value
            # doesn't change its max/min), so these are safe to keep as
            # ordinary annotations sharing the "vintages" join above.
            #
            # Matches latest_vintage's own "-year" pick, so sorting by it
            # agrees with what wine_card.html/wine_detail.html show as the
            # wine's (single, representative) vintage.
            vintage_year=Max("vintages__year"),
            # Soonest due date across all of the wine's vintages, for the
            # "Drink By" sort - matches the reminder feature's framing that
            # the most urgent vintage is the one that matters for sorting.
            next_drink_by=Min("vintages__drink_by"),
        )
        qs = qs.prefetch_related("grapes", latest_vintage_prefetch())
        return qs.filter(user=self.request.user)


class WineScanView(TemplateView):
    template_name = "wine_scan.html"


class WineScannedView(TemplateView):
    template_name = "wine_scanned.html"

    def dispatch(self, request, *args, **kwargs):
        barcode = self.kwargs["barcode"]
        # A 2-row slice distinguishes "exactly one match" from "more than
        # one" in a single query, instead of a separate count() + first().
        vintages = list(
            Vintage.objects.filter(
                barcode=barcode, wine__user=self.request.user
            ).select_related("wine")[:2]
        )
        if len(vintages) == 1:
            url = reverse("wine-detail", kwargs={"pk": vintages[0].wine.pk})
            return redirect(f"{url}?vintage={vintages[0].pk}")
        if len(vintages) > 1:
            return redirect(reverse("wine-scan-multiple", kwargs={"barcode": barcode}))

        return super().dispatch(request, *args, **kwargs)


class WineScanMultipleView(TemplateView):
    template_name = "wine_scan_multiple.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        barcode = self.kwargs["barcode"]
        vintages = list(
            Vintage.objects.filter(
                barcode=barcode, wine__user=self.request.user
            ).select_related("wine")
        )
        context.update(
            {
                "barcode": barcode,
                "same_wine": len({v.wine_id for v in vintages}) == 1,
                "vintages": vintages,
            }
        )
        return context


class WineDeleteView(DeleteView):
    model = Wine
    template_name = "wine_confirm_delete.html"
    success_url = reverse_lazy("wine-list")

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        with transaction.atomic():
            # Log before the cascade delete removes the StorageItems, so any
            # still-active bottle gets its own REMOVED event first.
            active_items = list(
                StorageItem.objects.filter(
                    vintage__wine=self.object, deleted=False
                ).select_related("vintage")
            )
            StorageItemEvent.objects.bulk_create(
                StorageItemEvent(
                    storage_item=item,
                    wine=self.object,
                    wine_name=self.object.name,
                    vintage=item.vintage,
                    vintage_year=item.vintage.year,
                    user=self.request.user,
                    event_type=StorageItemEventType.REMOVED,
                    note=_("Removed automatically because the wine was deleted."),
                )
                for item in active_items
            )
            StorageItemEvent.objects.create(
                wine=self.object,
                wine_name=self.object.name,
                user=self.request.user,
                event_type=StorageItemEventType.WINE_REMOVED,
            )
            self.object.delete()
        return redirect(success_url)


class VintageCreateView(FormView):
    template_name = "vintage_form.html"
    form_class = VintageForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("user", self.request.user)
        kwargs.setdefault("wine", self.get_wine())
        return kwargs

    def get_wine(self):
        if not hasattr(self, "_wine"):
            self._wine = get_object_or_404(
                Wine, pk=self.kwargs["wine_pk"], user=self.request.user
            )
        return self._wine

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wine"] = self.get_wine()
        return context

    def form_valid(self, form):
        wine = self.get_wine()
        cleaned_data = form.cleaned_data
        user = self.request.user
        vintage = Vintage(wine=wine, user=user)
        for field in VINTAGE_FIELDS:
            setattr(vintage, field, cleaned_data.get(field))
        try:
            vintage.save()
        except IntegrityError:
            # Backstop for the race between clean_year()'s check and this
            # save() - clean_year() already catches the common case.
            form.add_error(
                "year", _("A vintage with this year already exists for this wine.")
            )
            return self.form_invalid(form)
        for form_field, image_type in image_fields_map.items():
            image = cleaned_data.get(form_field)
            if image and not hasattr(image, "instance"):
                WineImage.objects.get_or_create(
                    image=image, vintage=vintage, user=user, image_type=image_type
                )
        self.success_url = reverse_lazy("wine-detail", kwargs={"pk": wine.pk})
        return super().form_valid(form)


class VintageUpdateView(FormView):
    template_name = "vintage_form.html"
    form_class = VintageForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        vintage = self.get_vintage()
        kwargs.setdefault("user", self.request.user)
        kwargs.setdefault("wine", vintage.wine)
        kwargs.setdefault("instance", vintage)
        return kwargs

    def get_vintage(self):
        if not hasattr(self, "_vintage"):
            self._vintage = get_object_or_404(
                Vintage,
                pk=self.kwargs["pk"],
                wine__pk=self.kwargs["wine_pk"],
                wine__user=self.request.user,
            )
        return self._vintage

    def get_initial(self):
        vintage = self.get_vintage()
        initial = super().get_initial()
        initial["vintage_id"] = vintage.pk
        for field in VINTAGE_FIELDS:
            initial[field] = getattr(vintage, field)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vintage = self.get_vintage()
        context["wine"] = vintage.wine
        context["vintage"] = vintage
        return context

    def form_valid(self, form):
        vintage = self.get_vintage()
        cleaned_data = form.cleaned_data
        user = self.request.user
        for field in VINTAGE_FIELDS:
            setattr(vintage, field, cleaned_data.get(field))
        try:
            vintage.save()
        except IntegrityError:
            # Backstop for the race between clean_year()'s check and this
            # save() - clean_year() already catches the common case.
            form.add_error(
                "year", _("A vintage with this year already exists for this wine.")
            )
            return self.form_invalid(form)
        for form_field, image_type in image_fields_map.items():
            image = cleaned_data.get(form_field)
            existing = WineImage.objects.filter(
                vintage=vintage, user=user, image_type=image_type
            )
            if image is False or (image and not hasattr(image, "instance")):
                old = existing.first()
                if old:
                    old.image.delete(save=False)
                    old.thumbnail.delete(save=False)
                    old.delete()
            if image and not hasattr(image, "instance"):
                WineImage.objects.get_or_create(
                    image=image, vintage=vintage, user=user, image_type=image_type
                )
        self.success_url = reverse_lazy("wine-detail", kwargs={"pk": vintage.wine.pk})
        return super().form_valid(form)


class VintageDeleteView(DeleteView):
    model = Vintage
    template_name = "vintage_confirm_delete.html"

    def get_queryset(self):
        return Vintage.objects.filter(
            wine__pk=self.kwargs["wine_pk"], wine__user=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wine"] = self.object.wine
        context["active_stock_count"] = StorageItem.objects.filter(
            vintage=self.object, deleted=False
        ).count()
        return context

    def get_success_url(self):
        return reverse_lazy("wine-detail", kwargs={"pk": self.object.wine.pk})

    def form_valid(self, form):
        vintage = self.object
        wine = vintage.wine
        if wine.vintages.count() <= 1:
            form.add_error(
                None,
                _(
                    "Cannot delete the last vintage. Delete the wine instead"
                    " to remove it entirely."
                ),
            )
            return self.form_invalid(form)
        success_url = self.get_success_url()
        with transaction.atomic():
            # Log before the cascade delete removes the StorageItems, so any
            # still-active bottle gets its own REMOVED event first - same
            # pattern as WineDeleteView.form_valid.
            active_items = list(
                StorageItem.objects.filter(
                    vintage=vintage, deleted=False
                ).select_related("vintage")
            )
            StorageItemEvent.objects.bulk_create(
                StorageItemEvent(
                    storage_item=item,
                    wine=wine,
                    wine_name=wine.name,
                    vintage=vintage,
                    vintage_year=vintage.year,
                    user=self.request.user,
                    event_type=StorageItemEventType.REMOVED,
                    note=_("Removed automatically because the vintage was deleted."),
                )
                for item in active_items
            )
            StorageItemEvent.objects.create(
                wine=wine,
                wine_name=wine.name,
                vintage=vintage,
                vintage_year=vintage.year,
                user=self.request.user,
                event_type=StorageItemEventType.VINTAGE_REMOVED,
            )
            self.object.delete()
        return redirect(success_url)


class WineMapView(TemplateView):
    template_name = "wine_map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wines = Wine.objects.filter(user=self.request.user).prefetch_related(
            latest_vintage_prefetch()
        )

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
            return JsonResponse(
                {
                    "errors": {
                        "__all__": [
                            str(_("Could not start the AI request. Please try again."))
                        ]
                    }
                },
                status=400,
            )

        return JsonResponse(
            {"poll_url": reverse("wine-ai-upload-poll", kwargs={"token": token})}
        )

    def form_invalid(self, form):
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)


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
