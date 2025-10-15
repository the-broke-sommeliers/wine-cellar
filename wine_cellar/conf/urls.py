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
from django.views.i18n import JavaScriptCatalog

from wine_cellar.apps.storage.views import (
    StorageCreateView,
    StorageDeleteView,
    StorageDetailView,
    StorageItemAddView,
    StorageItemDeleteView,
    StorageListView,
    StorageUpdateView,
)
from wine_cellar.apps.user.views import UserSettingsView
from wine_cellar.apps.wine.views import (
    HomePageView,
    WineCreateView,
    WineDeleteView,
    WineDetailView,
    WineListView,
    WineMapView,
    WineScannedView,
    WineScanView,
    WineUpdateView,
    health_check,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("user/settings/", UserSettingsView.as_view(), name="user-settings"),
    path("storages/", StorageListView.as_view(), name="storage-list"),
    path("storage/<int:pk>", StorageDetailView.as_view(), name="storage-detail"),
    path("storage/add/", StorageCreateView.as_view(), name="storage-add"),
    path("storage/delete/<int:pk>", StorageDeleteView.as_view(), name="storage-delete"),
    path("storage/edit/<int:pk>", StorageUpdateView.as_view(), name="storage-edit"),
    path("stock/add/<int:pk>", StorageItemAddView.as_view(), name="stock-add"),
    path("stock/delete/<int:pk>", StorageItemDeleteView.as_view(), name="stock-delete"),
    path("wine/add/", WineCreateView.as_view(), name="wine-add"),
    path("wine/add/<str:code>", WineCreateView.as_view(), name="wine-add"),
    path("wine/<int:pk>", WineDetailView.as_view(), name="wine-detail"),
    path("wine/edit/<int:pk>", WineUpdateView.as_view(), name="wine-edit"),
    path("wine/delete/<int:pk>", WineDeleteView.as_view(), name="wine-delete"),
    path("wines/", WineListView.as_view(), name="wine-list"),
    path("wine/scan", WineScanView.as_view(), name="wine-scan"),
    path("wine/scan/<str:code>", WineScannedView.as_view(), name="wine-scan"),
    path("wines/map", WineMapView.as_view(), name="wine-map"),
    path("health/", health_check, name="health_check"),
    path("", HomePageView.as_view(), name="homepage"),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
