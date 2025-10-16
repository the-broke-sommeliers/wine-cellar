from django.forms import model_to_dict
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, FormView, ListView
from django.views.generic.list import MultipleObjectMixin

from wine_cellar.apps.storage.forms import StockAddForm, StorageForm
from wine_cellar.apps.storage.models import Storage, StorageItem
from wine_cellar.apps.wine.models import Wine


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
        object_list = object.get_wines
        context = super(StorageDetailView, self).get_context_data(
            object_list=object_list, **kwargs
        )
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

        Storage.objects.create(
            location=location,
            description=description,
            name=name,
            rows=rows,
            columns=columns,
            user=user,
        )


class StorageUpdateView(FormView):
    template_name = "storage_edit.html"
    form_class = StorageForm
    success_url = reverse_lazy("storage-list")

    def get_initial(self):
        initial = super().get_initial()
        storage = get_object_or_404(Storage, pk=self.kwargs["pk"])
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

        storage.location = location
        storage.description = description
        storage.name = name
        storage.rows = rows
        storage.columns = columns
        storage.user = user
        storage.save()


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
                    "You must have at least one storage."
                    + " Cannot delete the last storage."
                ),
            )
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class StorageItemAddView(FormView):
    template_name = "stock_add.html"
    form_class = StockAddForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "user" not in kwargs:
            kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_storages = Storage.objects.filter(user=self.request.user)
        free_cells_by_storage = {}
        for storage in user_storages:
            if storage.rows == 0:
                free_cells_by_storage[storage.pk] = {
                    "free_rows": None,
                    "free_columns": None,
                }
                continue
            used_cells = set(storage.items.values_list("row", "column"))
            all_rows = range(1, storage.rows + 1)
            all_columns = range(1, storage.columns + 1)
            free_cells = [
                (r, c)
                for r in all_rows
                for c in all_columns
                if (r, c) not in used_cells
            ]
            free_rows = sorted(set(r for r, _ in free_cells))
            free_columns = sorted(set(c for _, c in free_cells))
            free_cells_by_storage[storage.pk] = {
                "free_rows": free_rows,
                "free_columns": free_columns,
            }
        context["free_cells_by_storage"] = free_cells_by_storage
        return context

    def form_valid(self, form):
        wine = get_object_or_404(Wine, pk=self.kwargs["pk"], user=self.request.user)
        self.process_form_data(wine, self.request.user, form.cleaned_data)
        self.success_url = reverse_lazy("wine-detail", kwargs={"pk": wine.pk})
        return super().form_valid(form)

    @staticmethod
    def process_form_data(wine, user, cleaned_data):
        storage = cleaned_data["storage"]
        row = cleaned_data["row"]
        column = cleaned_data["column"]

        StorageItem.objects.create(
            storage=storage,
            wine=wine,
            row=row,
            column=column,
            user=user,
        )


class StorageItemDeleteView(DeleteView):
    model = StorageItem
    template_name = "storage_item_confirm_delete.html"

    def get_success_url(self):
        next = self.request.GET.get("next")
        if next == "storage":
            return reverse_lazy("storage-detail", kwargs={"pk": self.object.storage.pk})
        return reverse_lazy("wine-detail", kwargs={"pk": self.object.wine.pk})

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)
