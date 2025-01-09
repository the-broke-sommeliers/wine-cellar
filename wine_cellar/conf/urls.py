"""
URL configuration for wine_cellar project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from wine_cellar.apps.wine.views import (
    HomePageView,
    WineChangeStockView,
    WineCreateView,
    WineDetailView,
    WineListView,
    WineScannedView,
    WineScanView,
    WineUpdateView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("wine/add/", WineCreateView.as_view(), name="wine-add"),
    path("wine/add/<str:code>", WineCreateView.as_view(), name="wine-add"),
    path("wine/<int:pk>", WineDetailView.as_view(), name="wine-detail"),
    path("wine/edit/<int:pk>", WineUpdateView.as_view(), name="wine-edit"),
    path("wines/", WineListView.as_view(), name="wine-list"),
    path("wine/scan", WineScanView.as_view(), name="wine-scan"),
    path("wine/scan/<str:code>", WineScannedView.as_view(), name="wine-scan"),
    path(
        "wine/change_stock/<int:pk><int:op>",
        WineChangeStockView.as_view(),
        name="change-stock",
    ),
    path("", HomePageView.as_view(), name="homepage"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
