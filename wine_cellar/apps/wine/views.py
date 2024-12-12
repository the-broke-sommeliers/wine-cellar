from backgroundremover import bg
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import model_to_dict
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, TemplateView
from django_filters.views import FilterView

from wine_cellar.apps.wine.filters import WineFilter
from wine_cellar.apps.wine.forms import WineEditForm, WineForm
from wine_cellar.apps.wine.models import Wine, WineImage


class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = "homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        wines = Wine.objects.count()
        wines_in_stock = Wine.objects.filter(stock__gt=0).count()
        countries = Wine.objects.values_list("country").distinct().count()
        oldest = "-"
        youngest = "-"
        try:
            oldest = (
                Wine.objects.filter(vintage__isnull=False).earliest("vintage").vintage
            )
            youngest = (
                Wine.objects.filter(vintage__isnull=False).latest("vintage").vintage
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


class WineCreateView(LoginRequiredMixin, FormView):
    template_name = "wine_create.html"
    form_class = WineForm
    success_url = reverse_lazy("wine-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "user" not in kwargs:
            kwargs["user"] = self.request.user
        return kwargs

    def form_invalid(self, form):
        form.data = form.data.copy()
        form.data["form_step"] = form.cleaned_data["form_step"]
        return super().form_invalid(form)

    def form_valid(self, form):
        form_step = form.cleaned_data.get("form_step", 4)
        # assume form_step is last step if not send
        if form_step is None:
            form_step = 4
        if form_step < 4:
            # FIXME: hacky workaround to increase form_step field
            form.data = form.data.copy()
            form.data["form_step"] = form.cleaned_data["form_step"] + 1
            return super().form_invalid(form)
        elif form_step == 4:
            self.process_form_data(self.request.user, form.cleaned_data)
            return super().form_valid(form)
        return super().form_invalid(form)

    @staticmethod
    def process_form_data(user, cleaned_data):
        abv = cleaned_data["abv"]
        size = cleaned_data["size"][0]
        category = cleaned_data["category"]
        comment = cleaned_data["comment"]
        country = cleaned_data["country"]
        food_pairings = cleaned_data["food_pairings"]
        source = cleaned_data["source"]
        vineyards = cleaned_data["vineyard"]
        grapes = cleaned_data["grapes"]
        remove_background = cleaned_data["remove_background"]
        image = cleaned_data["image"]
        name = cleaned_data["name"]
        rating = cleaned_data["rating"]
        stock = cleaned_data["stock"]
        vintage = cleaned_data["vintage"]
        wine_type = cleaned_data["wine_type"]

        wine = Wine(
            abv=abv,
            size=size,
            category=category,
            country=country,
            name=name,
            stock=stock if stock else 0,
            user=user,
            vintage=vintage,
            wine_type=wine_type,
            comment=comment,
            rating=rating,
        )
        wine.save()

        wine.vineyard.set(vineyards),
        wine.grapes.set(grapes)
        wine.food_pairings.set(food_pairings)
        wine.source.set(source)
        if image:
            wine_image, _ = WineImage.objects.get_or_create(
                image=image, wine=wine, user=user
            )
            if remove_background:
                model_choices = ["u2net", "u2net_human_seg", "u2netp"]
                f = open(wine_image.image.path, "rb")
                data = f.read()
                f.close()
                img = bg.remove(
                    data,
                    model_name=model_choices[0],
                    alpha_matting=True,
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_structure_size=10,
                    alpha_matting_base_size=1000,
                )
                f = open(wine_image.image.path, "wb")
                f.write(img)
                f.close()


class WineUpdateView(LoginRequiredMixin, FormView):
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
        wine = get_object_or_404(Wine, pk=self.kwargs["pk"])
        initial.update(model_to_dict(wine))
        return initial

    def form_valid(self, form):
        wine = get_object_or_404(Wine, pk=self.kwargs["pk"])
        if not self.request.user == wine.user:
            return HttpResponseForbidden()
        self.process_form_data(wine, self.request.user, form.cleaned_data)
        return super().form_valid(form)

    @staticmethod
    def process_form_data(wine, user, cleaned_data):
        abv = cleaned_data["abv"]
        size = cleaned_data["size"][0]
        category = cleaned_data["category"]
        comment = cleaned_data["comment"]
        country = cleaned_data["country"]
        food_pairings = cleaned_data["food_pairings"]
        source = cleaned_data["source"]
        vineyards = cleaned_data["vineyard"]
        grapes = cleaned_data["grapes"]
        remove_background = cleaned_data["remove_background"]
        image = cleaned_data["image"]
        name = cleaned_data["name"]
        rating = cleaned_data["rating"]
        stock = cleaned_data["stock"]
        vintage = cleaned_data["vintage"]
        wine_type = cleaned_data["wine_type"]

        wine.abv = abv
        wine.size = size
        wine.category = category
        wine.comment = comment
        wine.country = country
        wine.name = name
        wine.rating = rating
        wine.stock = stock if stock else 0
        wine.vintage = vintage
        wine.wine_type = wine_type
        wine.save()

        wine.vineyard.set(vineyards)
        wine.grapes.set(grapes)
        wine.food_pairings.set(food_pairings)
        wine.source.set(source)

        if image:
            existing_image = WineImage.objects.filter(wine=wine, user=user)
            if existing_image.exists():
                existing_image.first().image.delete()
                existing_image.delete()
            wine_image, _ = WineImage.objects.get_or_create(
                image=image, wine=wine, user=user
            )
            if remove_background:
                model_choices = ["u2net", "u2net_human_seg", "u2netp"]
                f = open(wine_image.image.path, "rb")
                data = f.read()
                f.close()
                img = bg.remove(
                    data,
                    model_name=model_choices[0],
                    alpha_matting=True,
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_structure_size=10,
                    alpha_matting_base_size=1000,
                )
                f = open(wine_image.image.path, "wb")
                f.write(img)
                f.close()


class WineDetailView(LoginRequiredMixin, DetailView):
    template_name = "wine_detail.html"
    model = Wine


class WineListView(LoginRequiredMixin, FilterView):
    model = Wine
    template_name = "wine_list.html"
    context_object_name = "wines"
    filterset_class = WineFilter
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().order_by("pk")
        return qs.filter(user=self.request.user)
