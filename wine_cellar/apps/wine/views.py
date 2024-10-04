import requests
from backgroundremover import bg
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, FormView
from django_filters.views import FilterView

from wine_cellar.apps.wine.filters import WineFilter
from wine_cellar.apps.wine.forms import WineEditForm, WineForm
from wine_cellar.apps.wine.models import Wine, WineImage


class HomePageView(View):
    template_name = "base.html"

    @method_decorator(csrf_exempt)
    async def dispatch(self, *args, **kwargs):
        return await super().dispatch(*args, **kwargs)

    async def get(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect("login")
        return render(request, self.template_name, {"user": user})


class WineCreateView(LoginRequiredMixin, FormView):
    template_name = "wine_create.html"
    form_class = WineForm
    success_url = reverse_lazy("wine-list")

    def form_valid(self, form):
        self.process_form_data(self.request.user, form.cleaned_data)
        return super().form_valid(form)

    @staticmethod
    def process_form_data(user, cleaned_data):
        abv = cleaned_data["abv"]
        capacity = cleaned_data["capacity"]
        category = cleaned_data["category"]
        comment = cleaned_data["comment"]
        country = cleaned_data["country"]
        food_pairings = cleaned_data["food_pairings"]
        source = cleaned_data["source"]
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
            capacity=capacity,
            category=category,
            country=country,
            name=name,
            stock=stock if stock else 0,
            user=user,
            vintage=vintage,
            wine_type=wine_type,
        )
        wine.comment = comment
        wine.rating = rating
        wine.save()
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


class WineUpdateView(View):
    template_name = "wine_create.html"

    def get(self, request, pk, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        wine = get_object_or_404(Wine, pk=pk)
        if not request.user == wine.user:
            return HttpResponseForbidden()
        form = WineEditForm(instance=wine)
        return render(request, self.template_name, {"form": form})

    def post(self, request, pk, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        wine = get_object_or_404(Wine, pk=pk)
        if not request.user == wine.user:
            return HttpResponseForbidden()
        form = WineForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            self.process_form_data(wine, request.user, form.cleaned_data)
            return redirect("wine-list")
        return render(request, self.template_name, {"form": form})

    @staticmethod
    def process_form_data(wine, user, cleaned_data):
        abv = cleaned_data["abv"]
        capacity = cleaned_data["capacity"]
        category = cleaned_data["category"]
        comment = cleaned_data["comment"]
        country = cleaned_data["country"]
        food_pairings = cleaned_data["food_pairings"]
        source = cleaned_data["source"]
        grapes = cleaned_data["grapes"]
        image = cleaned_data["image"]
        name = cleaned_data["name"]
        rating = cleaned_data["rating"]
        stock = cleaned_data["stock"]
        vintage = cleaned_data["vintage"]
        wine_type = cleaned_data["wine_type"]

        wine.abv = abv
        wine.capacity = capacity
        wine.category = category
        wine.comment = comment
        wine.country = country
        wine.name = name
        wine.rating = rating
        wine.stock = stock if stock else 0
        wine.vintage = vintage
        wine.wine_type = wine_type

        wine.grapes.set(grapes)
        wine.food_pairings.set(food_pairings)
        wine.source.set(source)
        wine.save()
        if image:
            WineImage.objects.get_or_create(image=image, wine=wine, user=user)


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


class WineSearchView(View):
    template_name = "wine_search.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect("login")
        wine_filter = WineFilter(request.GET, queryset=None)
        return render(
            request, self.template_name, {"user": user, "wine_filter": wine_filter}
        )


class WineRemoteSearchView(View):
    template_name = "wine_remote_search.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        wine_filter = WineFilter(request.GET, queryset=Wine.objects.all())
        # TODO: include local results
        # r = requests.get("http://127.0.0.1:8003/wines/", params={**request.GET})
        r = requests.get("http://127.0.0.1:8009/wines/", params={**request.GET})
        results = r.json()
        return render(
            request,
            self.template_name,
            {"results": results, "user": request.user, "wine_filter": wine_filter},
        )
