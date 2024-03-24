from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt


class UserProfileView(View):
    template_name = "user_profile.html"

    @method_decorator(csrf_exempt)
    async def dispatch(self, *args, **kwargs):
        return await super().dispatch(*args, **kwargs)

    async def get(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect("login")
        return render(request, self.template_name, {"user": user})


class SettingsView(View):
    template_name = "settings.html"

    @method_decorator(csrf_exempt)
    async def dispatch(self, *args, **kwargs):
        return await super().dispatch(*args, **kwargs)

    async def get(self, request, *args, **kwargs):
        user = await request.auser()
        if not user.is_authenticated:
            return redirect("login")
        return render(request, self.template_name, {"user": user})
