from django.contrib.auth.decorators import login_not_required
from django.db import connections
from django.forms import model_to_dict
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, DetailView, FormView, TemplateView
from django_filters.views import FilterView

from wine_cellar.apps.wine.filters import WineFilter
from wine_cellar.apps.wine.forms import WineEditForm, WineForm, image_fields_map
from wine_cellar.apps.wine.models import Wine, WineImage


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

        context.update(
            {
                "wines": wines,
                "wines_in_stock": wines_in_stock,
                "countries": countries,
                "oldest": oldest,
                "youngest": youngest,
            }
        )
        return context


class WineCreateView(FormView):
    template_name = "wine_create.html"
    form_class = WineForm
    success_url = reverse_lazy("wine-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "user" not in kwargs:
            kwargs["user"] = self.request.user
        if "code" in self.kwargs:
            kwargs["initial"].update({"barcode": self.kwargs["code"]})
        return kwargs

    def form_valid(self, form):
        form_step = form.cleaned_data.get("form_step", 4)

        # assume form_step is last step if not send
        if form_step is None:
            form_step = 4
        if form_step == 4 or "save_finish" in self.request.POST:
            self.process_form_data(self.request.user, form.cleaned_data)
            return super().form_valid(form)
        elif form_step < 4:
            # FIXME: hacky workaround to increase form_step field
            form.data = form.data.copy()
            form.data["form_step"] = form.cleaned_data["form_step"] + 1
            return super().form_invalid(form)

        return super().form_invalid(form)

    @staticmethod
    def process_form_data(user, cleaned_data):
        abv = cleaned_data["abv"]
        size = cleaned_data["size"][0]
        category = cleaned_data["category"]
        barcode = cleaned_data["barcode"]
        comment = cleaned_data["comment"]
        country = cleaned_data["country"]
        food_pairings = cleaned_data["food_pairings"]
        source = cleaned_data["source"]
        price = cleaned_data["price"]
        vineyards = cleaned_data["vineyard"]
        grapes = cleaned_data["grapes"]
        name = cleaned_data["name"]
        rating = cleaned_data["rating"]
        vintage = cleaned_data["vintage"]
        wine_type = cleaned_data["wine_type"]
        attributes = cleaned_data["attributes"]
        drink_by = cleaned_data["drink_by"]

        wine = Wine(
            abv=abv,
            size=size,
            category=category,
            country=country,
            name=name,
            barcode=barcode,
            user=user,
            vintage=vintage,
            drink_by=drink_by,
            wine_type=wine_type,
            comment=comment,
            rating=rating,
            price=price,
        )
        wine.save()

        wine.vineyard.set(vineyards),
        wine.grapes.set(grapes)
        wine.food_pairings.set(food_pairings)
        wine.source.set(source)
        wine.attributes.set(attributes)

        for form_field, image_type in image_fields_map.items():
            image = cleaned_data.get(form_field)
            if image:
                WineImage.objects.get_or_create(
                    image=image, wine=wine, user=user, image_type=image_type
                )


class WineUpdateView(FormView):
    template_name = "wine_edit.html"
    form_class = WineEditForm
    success_url = reverse_lazy("wine-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "user" not in kwargs:
            kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        wine = get_object_or_404(Wine, pk=self.kwargs["pk"], user=self.request.user)
        initial.update(model_to_dict(wine))
        return initial

    def form_valid(self, form):
        wine = get_object_or_404(Wine, pk=self.kwargs["pk"], user=self.request.user)
        self.process_form_data(wine, self.request.user, form.cleaned_data)
        self.success_url = reverse_lazy("wine-detail", kwargs={"pk": wine.pk})
        return super().form_valid(form)

    @staticmethod
    def process_form_data(wine, user, cleaned_data):
        abv = cleaned_data["abv"]
        size = cleaned_data["size"][0]
        category = cleaned_data["category"]
        barcode = cleaned_data["barcode"]
        comment = cleaned_data["comment"]
        country = cleaned_data["country"]
        food_pairings = cleaned_data["food_pairings"]
        source = cleaned_data["source"]
        price = cleaned_data["price"]
        vineyards = cleaned_data["vineyard"]
        grapes = cleaned_data["grapes"]
        name = cleaned_data["name"]
        rating = cleaned_data["rating"]
        vintage = cleaned_data["vintage"]
        drink_by = cleaned_data["drink_by"]
        wine_type = cleaned_data["wine_type"]
        attributes = cleaned_data["attributes"]

        wine.abv = abv
        wine.size = size
        wine.category = category
        wine.comment = comment
        wine.country = country
        wine.name = name
        wine.barcode = barcode
        wine.rating = rating
        wine.vintage = vintage
        wine.drink_by = drink_by
        wine.wine_type = wine_type
        wine.price = price
        wine.save()

        wine.vineyard.set(vineyards)
        wine.grapes.set(grapes)
        wine.food_pairings.set(food_pairings)
        wine.attributes.set(attributes)
        wine.source.set(source)

        for form_field, image_type in image_fields_map.items():
            image = cleaned_data.get(form_field)
            existing_image = WineImage.objects.filter(
                wine=wine, user=user, image_type=image_type
            )
            if image is False or not hasattr(image, "instance"):
                if existing_image.exists():
                    existing_image.first().image.delete()
                    existing_image.delete()
            if image and not hasattr(image, "instance"):
                WineImage.objects.get_or_create(
                    image=image, wine=wine, user=user, image_type=image_type
                )


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
        return qs.filter(user=self.request.user)


class WineScanView(TemplateView):
    template_name = "scan_wine.html"


class WineScannedView(TemplateView):
    template_name = "scanned_wine.html"

    def dispatch(self, request, *args, **kwargs):
        code = self.kwargs["code"]
        wine = Wine.objects.filter(barcode=code).filter(user=self.request.user).first()
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


@login_not_required
def health_check(request):
    db_ok = all(conn.cursor().execute("SELECT 1") for conn in connections.all())
    status_code = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "unhealthy"}, status=status_code)
