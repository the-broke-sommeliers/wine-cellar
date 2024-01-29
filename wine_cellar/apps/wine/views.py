from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q, OuterRef, Subquery
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from wine_cellar.apps.wine.forms import WineForm
from wine_cellar.apps.wine.models import Wine, Rating


class WineCreateView(View):
    template_name = 'wine_form.html'

    @method_decorator(csrf_exempt)
    async def dispatch(self, *args, **kwargs):
        return await super().dispatch(*args, **kwargs)

    async def get(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
           return redirect('login')
        form = WineForm()
        return render(request, self.template_name, {'form': form})

    async def post(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect('login')
        form = WineForm(request.POST)
        if form.is_valid():
            await self.process_form_data(user, form.cleaned_data)
            return redirect('wine-list')
        return render(request, self.template_name, {'form': form})

    @staticmethod
    async def process_form_data(user, cleaned_data):
        name = cleaned_data['name']
        wine_type = cleaned_data['wine_type']
        abv = cleaned_data['abv']
        capacity = cleaned_data['capacity']
        vintage = cleaned_data['vintage']
        comment = cleaned_data['comment']
        rating = cleaned_data['rating']

        wine = Wine(name=name, wine_type=wine_type, abv=abv, capacity=capacity, vintage=vintage, comment=comment)
        await wine.asave()
        rating_obj = Rating(value=rating, wine=wine, user=user)
        await rating_obj.asave()
        print(rating_obj.value)


class WineListView(ListView):
    model = Wine
    template_name = 'wine_list.html'
    context_object_name = 'wines'

    def get_queryset(self):
        qs = super().get_queryset()
        rating = Rating.objects.filter(wine=OuterRef("pk")).filter(user=self.request.user)
        qs = qs.annotate(user_rating=Subquery(rating.values("value")))
        print(qs.first().user_rating)
        return qs



