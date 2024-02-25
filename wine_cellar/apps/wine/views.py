import requests
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_filters.views import FilterView

from wine_cellar.apps.wine.filters import WineFilter
from wine_cellar.apps.wine.forms import WineForm
from wine_cellar.apps.wine.models import Vintage, Wine, WineImage


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


class WineCreateView(View):
    template_name = "wine_create.html"

    @method_decorator(csrf_exempt)
    async def dispatch(self, *args, **kwargs):
        return await super().dispatch(*args, **kwargs)

    async def get(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect("login")
        form = WineForm()
        return render(request, self.template_name, {"form": form, "user": user})

    async def post(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect("login")
        form = WineForm(request.POST, request.FILES)
        if form.is_valid():
            await self.process_form_data(user, form.cleaned_data)
            return redirect("wine-list")
        return render(request, self.template_name, {"form": form, "user": user})

    @staticmethod
    async def process_form_data(user, cleaned_data):
        name = cleaned_data["name"]
        wine_type = cleaned_data["wine_type"]
        abv = cleaned_data["abv"]
        capacity = cleaned_data["capacity"]
        vintage = cleaned_data["vintage"]
        comment = cleaned_data["comment"]
        rating = cleaned_data["rating"]
        image = cleaned_data["image"]

        wine = Wine(
            name=name,
            user=user,
            wine_type=wine_type,
            abv=abv,
            capacity=capacity,
            comment=comment,
            rating=rating,
        )
        await wine.asave()
        v, _ = await Vintage.objects.aget_or_create(name=vintage)
        await wine.vintage.aadd(v)
        if image:
            await WineImage.objects.aget_or_create(image=image, wine=wine, user=user)


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
    async def dispatch(self, *args, **kwargs):
        return await super().dispatch(*args, **kwargs)

    async def get(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return HttpResponseForbidden()
        wine_filter = WineFilter(request.GET, queryset=Wine.objects.all())
        # TODO: include local results
        # r = requests.get("http://127.0.0.1:8003/wines/", params={**request.GET})
        r = requests.get("http://127.0.0.1:8009/wines/", params={**request.GET})
        results = r.json()
        return render(
            request,
            self.template_name,
            {"results": results, "user": user, "wine_filter": wine_filter},
        )
