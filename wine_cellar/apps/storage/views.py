from datetime import timedelta

from django.core.paginator import Paginator
from django.db import IntegrityError, models, transaction
from django.forms import model_to_dict
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView
from django.views.generic.list import MultipleObjectMixin

from wine_cellar.apps.storage.forms import StockForm, StockOpenForm, StorageForm
from wine_cellar.apps.storage.models import (
    Storage,
    StorageItem,
    StorageItemEvent,
    StorageItemEventType,
    StorageLabel,
    StorageLabelAxis,
)
from wine_cellar.apps.wine.models import Vintage


class SlotConflictError(Exception):
    """Raised when a slot is no longer free once the lock is acquired."""


class StorageListView(ListView):
    model = Storage
    template_name = "storage_list.html"
    context_object_name = "storages"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().order_by("created")
        return qs.filter(user=self.request.user)


class StorageDetailView(DetailView, MultipleObjectMixin):
    template_name = "storage_detail.html"
    model = Storage
    paginate_by = 10

    def get_context_data(self, **kwargs):
        object = self.get_object()
        items = list(object.get_wines)
        swap_axes = object.swap_axes

        # Build a combined list of items and empty slots, sorted by grid position
        rows = []
        for item in items:
            rows.append(item)

        if object.rows > 0 and object.columns > 0:
            used = set(
                object.items.filter(deleted=False, row__isnull=False).values_list(
                    "row", "column"
                )
            )
            for r in range(1, object.rows + 1):
                for c in range(1, object.columns + 1):
                    if (r, c) not in used:
                        rows.append(
                            {
                                "is_empty": True,
                                "row": r,
                                "column": c,
                            }
                        )

        row_labels = object.row_labels
        column_labels = object.column_labels
        for entry in rows:
            row = entry["row"] if isinstance(entry, dict) else entry.row
            column = entry["column"] if isinstance(entry, dict) else entry.column
            row_label = row_labels.get(row)
            column_label = column_labels.get(column)
            if isinstance(entry, dict):
                entry["row_label"] = row_label
                entry["column_label"] = column_label
            else:
                entry.row_label = row_label
                entry.column_label = column_label

        def sort_key(x):
            r = x["row"] if isinstance(x, dict) else x.row
            c = x["column"] if isinstance(x, dict) else x.column
            return object.sort_key(r, c)

        rows.sort(key=sort_key)

        context = super(StorageDetailView, self).get_context_data(
            object_list=rows, **kwargs
        )
        context["swap_axes"] = swap_axes
        context["row_labels_enabled"] = object.row_labels_enabled
        context["column_labels_enabled"] = object.column_labels_enabled
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class StorageCreateView(FormView):
    template_name = "storage_create.html"
    form_class = StorageForm
    success_url = reverse_lazy("storage-list")

    def form_valid(self, form):
        self.process_form_data(self.request.user, form.cleaned_data)
        return super().form_valid(form)

    @staticmethod
    def process_form_data(user, cleaned_data):
        location = cleaned_data["location"]
        description = cleaned_data["description"]
        name = cleaned_data["name"]
        rows = cleaned_data["rows"] or 0
        columns = cleaned_data["columns"] or 0
        swap_axes = cleaned_data["swap_axes"]
        row_labels_enabled = cleaned_data["row_labels_enabled"]
        column_labels_enabled = cleaned_data["column_labels_enabled"]

        Storage.objects.create(
            location=location,
            description=description,
            name=name,
            rows=rows,
            columns=columns,
            swap_axes=swap_axes,
            row_labels_enabled=row_labels_enabled,
            column_labels_enabled=column_labels_enabled,
            user=user,
        )


class StorageUpdateView(FormView):
    template_name = "storage_edit.html"
    form_class = StorageForm
    success_url = reverse_lazy("storage-list")

    def get_initial(self):
        initial = super().get_initial()
        storage = get_object_or_404(
            Storage, pk=self.kwargs["pk"], user=self.request.user
        )
        initial.update(model_to_dict(storage))
        return initial

    def form_valid(self, form):
        storage = get_object_or_404(
            Storage, pk=self.kwargs["pk"], user=self.request.user
        )
        self.process_form_data(storage, self.request.user, form.cleaned_data)
        self.success_url = reverse_lazy("storage-detail", kwargs={"pk": storage.pk})
        return super().form_valid(form)

    @staticmethod
    def process_form_data(storage, user, cleaned_data):
        location = cleaned_data["location"]
        description = cleaned_data["description"]
        name = cleaned_data["name"]
        rows = cleaned_data["rows"]
        columns = cleaned_data["columns"]
        swap_axes = cleaned_data["swap_axes"]
        row_labels_enabled = cleaned_data["row_labels_enabled"]
        column_labels_enabled = cleaned_data["column_labels_enabled"]

        storage.location = location
        storage.description = description
        storage.name = name
        storage.rows = rows
        storage.columns = columns
        storage.swap_axes = swap_axes
        storage.row_labels_enabled = row_labels_enabled
        storage.column_labels_enabled = column_labels_enabled
        storage.user = user
        storage.save()


class StorageLabelsView(View):
    """Dedicated screen to name every row (or every column) of a storage's
    grid, one page of PAGE_SIZE indices at a time. Only ever touches the
    single axis + page it was called with - saving one page/axis must never
    delete or blank out labels belonging to a different page or axis."""

    template_name = "storage_labels.html"
    PAGE_SIZE = 25

    @staticmethod
    def _get_storage_and_count(request, pk, axis):
        if axis not in (StorageLabelAxis.ROW, StorageLabelAxis.COLUMN):
            raise Http404("Unknown axis")
        storage = get_object_or_404(Storage, pk=pk, user=request.user)
        enabled = (
            storage.row_labels_enabled
            if axis == StorageLabelAxis.ROW
            else storage.column_labels_enabled
        )
        if not enabled:
            raise Http404("Labels disabled for this axis")
        count = storage.rows if axis == StorageLabelAxis.ROW else storage.columns
        return storage, count

    @classmethod
    def _get_page(cls, count, page_number):
        # Single source of truth for how `count` indices are sliced into
        # pages - GET and POST must call this identically so "page N" always
        # means the same set of indices.
        return Paginator(range(1, count + 1), cls.PAGE_SIZE).get_page(page_number)

    def get(self, request, pk, axis):
        storage, count = self._get_storage_and_count(request, pk, axis)
        labels = (
            storage.row_labels
            if axis == StorageLabelAxis.ROW
            else storage.column_labels
        )
        page_obj = self._get_page(count, request.GET.get("page"))
        context = {
            "storage": storage,
            "axis": axis,
            "page_obj": page_obj,
            "entries": [(i, labels.get(i, "")) for i in page_obj.object_list],
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, axis):
        storage, count = self._get_storage_and_count(request, pk, axis)
        # Recompute the exact slice for the page that was SUBMITTED (hidden
        # field), not request.GET - and only ever touch those indices.
        page_obj = self._get_page(count, request.POST.get("page"))

        with transaction.atomic():
            for index in page_obj.object_list:
                name = request.POST.get(f"{axis}_{index}", "").strip()[:100]
                if name:
                    StorageLabel.objects.update_or_create(
                        storage=storage,
                        axis=axis,
                        index=index,
                        defaults={"name": name, "user": request.user},
                    )
                else:
                    StorageLabel.objects.filter(
                        storage=storage, axis=axis, index=index
                    ).delete()

        url = reverse("storage-labels", kwargs={"pk": storage.pk, "axis": axis})
        return redirect(f"{url}?page={page_obj.number}")


class StorageDeleteView(DeleteView):
    model = Storage
    template_name = "storage_confirm_delete.html"
    success_url = reverse_lazy("storage-list")

    def form_valid(self, form):
        storages = Storage.objects.filter(user=self.request.user).count()
        if storages <= 1:
            form.add_error(
                None,
                _(
                    "You must have at least one storage. "
                    "Cannot delete the last storage."
                ),
            )
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


def storage_picker_payload(user, exclude_item=None):
    """Per-storage JSON payload for the `stock_add.ts` slot picker."""
    storages = list(Storage.objects.filter(user=user))
    gridded = [storage for storage in storages if not storage.is_unlimited]
    if gridded:
        # Two queries total for however many gridded storages the user has,
        # instead of grid_cells()/row_labels/column_labels each re-querying
        # per storage - skipped entirely for unlimited-only storages.
        models.prefetch_related_objects(
            gridded,
            models.Prefetch(
                "items",
                queryset=StorageItem.objects.filter(deleted=False, row__isnull=False),
                to_attr="_prefetched_grid_items",
            ),
            models.Prefetch("labels", to_attr="_prefetched_labels"),
        )

    payload = {}
    for storage in storages:
        if storage.is_unlimited:
            payload[storage.pk] = {"unlimited": True}
            continue
        payload[storage.pk] = {
            "unlimited": False,
            "rows": storage.rows,
            "columns": storage.columns,
            "swap_axes": storage.swap_axes,
            "row_labels": storage.row_labels,
            "column_labels": storage.column_labels,
            "cells": storage.grid_cells(exclude_item=exclude_item),
        }
    return payload


class StorageItemAddView(FormView):
    template_name = "stock_add.html"
    form_class = StockForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "user" not in kwargs:
            kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["storage_cells_data"] = storage_picker_payload(self.request.user)
        context["is_edit"] = False
        # Display-only - not scoped to request.user like form_valid()'s
        # lookup: this is just the heading label, and re-renders on a form
        # error must not 404 the whole page over an unrelated field error.
        context["vintage"] = get_object_or_404(
            Vintage.objects.select_related("wine"), pk=self.kwargs["pk"]
        )
        return context

    def form_valid(self, form):
        vintage = get_object_or_404(
            Vintage, pk=self.kwargs["pk"], wine__user=self.request.user
        )
        try:
            self.process_form_data(vintage, self.request.user, form.cleaned_data)
        except (SlotConflictError, IntegrityError):
            form.add_error(
                None,
                _(
                    "One or more of the selected slots are no longer free."
                    " Please reselect."
                ),
            )
            return self.form_invalid(form)
        self.success_url = reverse_lazy("wine-detail", kwargs={"pk": vintage.wine.pk})
        return super().form_valid(form)

    @staticmethod
    def process_form_data(vintage, user, cleaned_data):
        storage = cleaned_data["storage"]
        price = cleaned_data.get("price")
        wine = vintage.wine

        with transaction.atomic():
            # Re-validate under lock - see SlotConflictError.
            storage = Storage.objects.select_for_update().get(pk=storage.pk)
            if storage.is_unlimited:
                quantity = cleaned_data.get("quantity") or 1
                items = StorageItem.objects.bulk_create(
                    StorageItem(
                        storage=storage, vintage=vintage, user=user, price=price
                    )
                    for _ in range(quantity)
                )
            else:
                requested = set(cleaned_data["slots"])
                if not requested <= set(storage.free_slots()):
                    raise SlotConflictError
                # ADDED events are created explicitly below - no save signal.
                items = StorageItem.objects.bulk_create(
                    StorageItem(
                        storage=storage,
                        vintage=vintage,
                        row=row,
                        column=column,
                        user=user,
                        price=price,
                    )
                    for row, column in cleaned_data["slots"]
                )
            StorageItemEvent.objects.bulk_create(
                StorageItemEvent(
                    storage_item=item,
                    wine=wine,
                    wine_name=wine.name,
                    vintage=vintage,
                    vintage_year=vintage.year,
                    user=user,
                    event_type=StorageItemEventType.ADDED,
                )
                for item in items
            )


class StorageItemUpdateView(FormView):
    template_name = "stock_add.html"
    form_class = StockForm

    def get_initial(self):
        initial = super().get_initial()
        self.storage_item = get_object_or_404(
            StorageItem.objects.select_related("vintage__wine"),
            pk=self.kwargs["pk"],
            user=self.request.user,
        )
        initial.update(model_to_dict(self.storage_item))
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "user" not in kwargs:
            kwargs["user"] = self.request.user
        if "storage_item" not in kwargs:
            kwargs["storage_item"] = self.storage_item
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["storage_cells_data"] = storage_picker_payload(
            self.request.user, exclude_item=self.storage_item
        )
        context["is_edit"] = True
        context["vintage"] = self.storage_item.vintage
        return context

    def get_success_url(self):
        next_param = self.request.GET.get("next")
        if next_param == "storage":
            return reverse_lazy(
                "storage-detail", kwargs={"pk": self.storage_item.storage.pk}
            )
        return reverse_lazy(
            "wine-detail", kwargs={"pk": self.storage_item.vintage.wine.pk}
        )

    def form_valid(self, form):
        try:
            self.process_form_data(
                self.storage_item,
                self.request.user,
                form.cleaned_data,
            )
        except (SlotConflictError, IntegrityError):
            form.add_error(
                None,
                _("The selected slot is no longer free. Please reselect."),
            )
            return self.form_invalid(form)
        self.success_url = self.get_success_url()
        return super().form_valid(form)

    @staticmethod
    def process_form_data(storage_item, user, cleaned_data):
        slots = cleaned_data["slots"]
        row, column = slots[0] if slots else (None, None)
        storage = cleaned_data["storage"]

        with transaction.atomic():
            # Re-validate under lock - see SlotConflictError.
            storage = Storage.objects.select_for_update().get(pk=storage.pk)
            if row is not None and (row, column) not in set(
                storage.free_slots(exclude_item=storage_item)
            ):
                raise SlotConflictError
            storage_item.storage = storage
            storage_item.row = row
            storage_item.column = column
            storage_item.price = cleaned_data.get("price")
            storage_item.user = user
            storage_item.save()


class StorageItemDeleteView(DeleteView):
    model = StorageItem
    template_name = "storage_item_confirm_delete.html"

    def get_success_url(self):
        next = self.request.GET.get("next")
        if next == "storage":
            return reverse_lazy("storage-detail", kwargs={"pk": self.object.storage.pk})
        return reverse_lazy("wine-detail", kwargs={"pk": self.object.vintage.wine.pk})

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user, deleted=False)

    def form_valid(self, form):
        self.object = self.get_object()
        with transaction.atomic():
            self.object.deleted = True
            self.object.save(update_fields=["deleted"])
            StorageItemEvent.objects.create(
                storage_item=self.object,
                wine=self.object.vintage.wine,
                wine_name=self.object.vintage.wine.name,
                vintage=self.object.vintage,
                vintage_year=self.object.vintage.year,
                user=self.request.user,
                event_type=StorageItemEventType.REMOVED,
            )
        return redirect(self.get_success_url())


class StorageItemOpenView(FormView):
    template_name = "stock_open.html"
    form_class = StockOpenForm

    def get_object(self):
        return get_object_or_404(
            StorageItem,
            pk=self.kwargs["pk"],
            user=self.request.user,
            deleted=False,
            opened=False,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["storage_item"] = self.get_object()
        return context

    def get_success_url(self):
        next_param = self.request.GET.get("next")
        if next_param == "storage":
            return reverse_lazy("storage-detail", kwargs={"pk": self.object.storage.pk})
        return reverse_lazy("wine-detail", kwargs={"pk": self.object.vintage.wine.pk})

    def form_valid(self, form):
        self.object = self.get_object()
        with transaction.atomic():
            note = form.cleaned_data.get("note") or None
            self.object.opened = True
            self.object.opened_note = note
            if form.cleaned_data.get("drink_in_days"):
                self.object.drink_by = timezone.localdate() + timedelta(
                    days=form.cleaned_data["drink_in_days"]
                )
            self.object.save(update_fields=["opened", "opened_note", "drink_by"])
            StorageItemEvent.objects.create(
                storage_item=self.object,
                wine=self.object.vintage.wine,
                wine_name=self.object.vintage.wine.name,
                vintage=self.object.vintage,
                vintage_year=self.object.vintage.year,
                user=self.request.user,
                event_type=StorageItemEventType.OPENED,
                note=note,
            )
        return redirect(self.get_success_url())


class StorageItemConsumeView(DeleteView):
    model = StorageItem
    template_name = "stock_consume.html"

    def get_success_url(self):
        next_param = self.request.GET.get("next")
        if next_param == "storage":
            return reverse_lazy("storage-detail", kwargs={"pk": self.object.storage.pk})
        return reverse_lazy("wine-detail", kwargs={"pk": self.object.vintage.wine.pk})

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user, deleted=False)

    def form_valid(self, form):
        self.object = self.get_object()
        with transaction.atomic():
            self.object.opened = True
            self.object.deleted = True
            self.object.save(update_fields=["opened", "deleted"])
            StorageItemEvent.objects.create(
                storage_item=self.object,
                wine=self.object.vintage.wine,
                wine_name=self.object.vintage.wine.name,
                vintage=self.object.vintage,
                vintage_year=self.object.vintage.year,
                user=self.request.user,
                event_type=StorageItemEventType.CONSUMED,
            )
        return redirect(self.get_success_url())


class StorageItemUndoOpenView(DeleteView):
    model = StorageItem
    template_name = "stock_undo_open.html"

    def get_success_url(self):
        next_param = self.request.GET.get("next")
        if next_param == "storage":
            return reverse_lazy("storage-detail", kwargs={"pk": self.object.storage.pk})
        return reverse_lazy("wine-detail", kwargs={"pk": self.object.vintage.wine.pk})

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user, deleted=False, opened=True)
        )

    def form_valid(self, form):
        self.object = self.get_object()
        with transaction.atomic():
            self.object.opened = False
            self.object.opened_note = None
            self.object.drink_by = None
            self.object.save(update_fields=["opened", "opened_note", "drink_by"])
            StorageItemEvent.objects.create(
                storage_item=self.object,
                wine=self.object.vintage.wine,
                wine_name=self.object.vintage.wine.name,
                vintage=self.object.vintage,
                vintage_year=self.object.vintage.year,
                user=self.request.user,
                event_type=StorageItemEventType.UNDO_OPEN,
            )
        return redirect(self.get_success_url())


class StorageItemHistoryView(ListView):
    model = StorageItemEvent
    template_name = "storage_item_history.html"
    context_object_name = "events"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        return (
            qs.filter(user=self.request.user)
            .select_related("storage_item__storage", "wine")
            .order_by("-created")
        )


def _adjacent(r1, c1, r2, c2, max_cols):
    """True if (r2, c2) is immediately before or after (r1, c1) in row-major order."""
    return _next_cell(r1, c1, max_cols) == (r2, c2) or _next_cell(r2, c2, max_cols) == (
        r1,
        c1,
    )


def _next_cell(row, col, max_cols):
    """Return the next cell in row-major order."""
    if col < max_cols:
        return (row, col + 1)
    return (row + 1, 1)


def _is_before(r1, c1, r2, c2):
    """True if (r1, c1) comes before (r2, c2)."""
    return r1 < r2 or (r1 == r2 and c1 < c2)


def _move_gap(storage, old_row, old_col, new_row, new_col):
    """Shift items between old and new toward the gap at old."""
    if _is_before(old_row, old_col, new_row, new_col):
        # old is before new: shift items backward toward old
        _shift_toward(storage, old_row, old_col, new_row, new_col, forward=False)
    else:
        # old is after new: shift items forward toward old
        _shift_toward(storage, new_row, new_col, old_row, old_col, forward=True)


def _shift_toward(storage, start_row, start_col, end_row, end_col, *, forward):
    """Shift items in [start, end] range toward one end."""
    max_cols = storage.columns
    if start_row == end_row:
        range_filter = models.Q(
            row=start_row, column__gte=start_col, column__lte=end_col
        )
    else:
        range_filter = (
            models.Q(row=start_row, column__gte=start_col)
            | models.Q(row__gt=start_row, row__lt=end_row)
            | models.Q(row=end_row, column__lte=end_col)
        )
    items = (
        StorageItem.objects.filter(
            storage=storage,
            deleted=False,
            row__isnull=False,
            column__isnull=False,
        )
        .filter(range_filter)
        .order_by("row", "column")
    )

    items = list(items)
    if not forward:
        items.reverse()

    destinations = []
    for item in items:
        if forward:
            destinations.append(_next_cell(item.row, item.column, max_cols))
        else:
            new_row = item.row - 1 if item.column == 1 else item.row
            new_col = max_cols if item.column == 1 else item.column - 1
            destinations.append((new_row, new_col))

    # Vacate everyone first so no write lands on a cell another shifted item
    # still occupies (would trip the unique constraint).
    for item in items:
        item.row = None
        item.column = None
    StorageItem.objects.bulk_update(items, ["row", "column"])

    for item, (new_row, new_col) in zip(items, destinations):
        item.row = new_row
        item.column = new_col
    StorageItem.objects.bulk_update(items, ["row", "column"])


class StorageItemSwapView(View):
    def post(self, request):
        source = get_object_or_404(
            StorageItem, pk=request.POST.get("item1"), user=request.user, deleted=False
        )

        target_id = request.POST.get("item2")
        target = None
        if target_id:
            target = get_object_or_404(
                StorageItem, pk=target_id, user=request.user, deleted=False
            )
            if source.storage_id != target.storage_id:
                return JsonResponse(
                    {"ok": False, "error": "Cannot move between different storages."},
                    status=400,
                )
        else:
            new_row = int(request.POST.get("row", 0))
            new_col = int(request.POST.get("column", 0))
            if source.storage_id != int(request.POST.get("storage", 0)):
                return JsonResponse(
                    {"ok": False, "error": "Cannot move between different storages."},
                    status=400,
                )
            if source.storage.columns > 0 and (
                new_row < 1
                or new_row > source.storage.rows
                or new_col < 1
                or new_col > source.storage.columns
            ):
                return JsonResponse({"ok": False, "error": "Invalid slot."}, status=400)

        try:
            with transaction.atomic():
                # Lock the storage, then re-read fresh - see SlotConflictError.
                storage = Storage.objects.select_for_update().get(pk=source.storage_id)
                source.refresh_from_db()
                if source.deleted:
                    raise SlotConflictError
                old_row, old_col = source.row, source.column

                if target is not None:
                    target.refresh_from_db()
                    if target.deleted or target.storage_id != storage.pk:
                        raise SlotConflictError
                    new_row, new_col = target.row, target.column
                elif storage.columns > 0 and storage.is_slot_occupied(new_row, new_col):
                    raise SlotConflictError

                if (
                    target is not None
                    and old_row is not None
                    and new_row is not None
                    and storage.columns > 0
                    and _adjacent(old_row, old_col, new_row, new_col, storage.columns)
                ):
                    # Adjacent cells: swap positions, vacating source first.
                    source.row, source.column = None, None
                    source.save(update_fields=["row", "column"])
                    target.row, target.column = old_row, old_col
                    target.save(update_fields=["row", "column"])
                    source.row, source.column = new_row, new_col
                    source.save(update_fields=["row", "column"])
                else:
                    source.row, source.column = None, None
                    source.save(update_fields=["row", "column"])

                    if (
                        target is not None
                        and old_row is not None
                        and new_row is not None
                        and storage.columns > 0
                    ):
                        _move_gap(storage, old_row, old_col, new_row, new_col)

                    source.row, source.column = new_row, new_col
                    source.save(update_fields=["row", "column"])
        except (SlotConflictError, IntegrityError):
            return JsonResponse({"ok": False, "error": "Slot is occupied."}, status=400)

        return JsonResponse({"ok": True})
