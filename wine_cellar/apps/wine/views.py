from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from wine_cellar.apps.wine.forms import WineForm
from wine_cellar.apps.wine.models import Wine


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
    template_name = "wine_form.html"

    @method_decorator(csrf_exempt)
    async def dispatch(self, *args, **kwargs):
        return await super().dispatch(*args, **kwargs)

    async def get(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect("login")
        form = WineForm()
        return render(request, self.template_name, {"form": form})

    async def post(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect("login")
        form = WineForm(request.POST)
        if form.is_valid():
            await self.process_form_data(user, form.cleaned_data)
            return redirect("wine-list")
        return render(request, self.template_name, {"form": form})

    @staticmethod
    async def process_form_data(user, cleaned_data):
        name = cleaned_data["name"]
        wine_type = cleaned_data["wine_type"]
        abv = cleaned_data["abv"]
        capacity = cleaned_data["capacity"]
        vintage = cleaned_data["vintage"]
        comment = cleaned_data["comment"]
        rating = cleaned_data["rating"]

        wine = Wine(
            name=name,
            wine_type=wine_type,
            abv=abv,
            capacity=capacity,
            vintage=vintage,
            comment=comment,
            rating=rating,
        )
        await wine.asave()


class WineListView(LoginRequiredMixin, ListView):
    model = Wine
    template_name = "wine_list.html"
    context_object_name = "wines"
