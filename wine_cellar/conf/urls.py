"""
URL configuration for wine_cellar project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from wine_cellar.apps.user.views import SettingsView, UserProfileView
from wine_cellar.apps.wine.views import (
    HomePageView,
    WineCreateView,
    WineListView,
    WineRemoteSearchView,
    WineSearchView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("wine/add/", WineCreateView.as_view(), name="wine-add"),
    path("wine/search/", WineSearchView.as_view(), name="wine-search"),
    path("wines/", WineListView.as_view(), name="wine-list"),
    path(
        "wine/search_remote/", WineRemoteSearchView.as_view(), name="wine-remote-search"
    ),
    path("", HomePageView.as_view(), name="homepage"),
    path("accounts/profile/", UserProfileView.as_view(), name="user-profile"),
    path("accounts/settings/", SettingsView.as_view(), name="settings"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
