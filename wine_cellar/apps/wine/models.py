from datetime import date, timedelta
from decimal import Decimal

import pycountry
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.wine.utils import user_directory_path


class UserContentModel(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class WineType(models.TextChoices):
    WHITE = "WH", _("White")
    RED = "RE", _("Red")
    ROSE = "RO", _("Rose")
    SPARKLING = "SP", _("Sparkling")
    DESSERT = "DE", _("Dessert")
    FORTIFIED = "FO", _("Fortified")
    ORANGE = "OR", _("Orange")


class Category(models.TextChoices):
    DRY = "DR", _("Dry")
    SEMI_DRY = "SD", _("Semi-Dry")
    MEDIUM_SWEET = "MS", _("Medium Sweet")
    SWEET = "SW", _("Sweet")
    FEINHERB = "FH", _("Feinherb")


class ImageType(models.TextChoices):
    FRONT = "FR", _("Front")
    BACK = "BA", _("Back")
    LABEL_FRONT = "LF", _("Label Front")
    LABEL_BACK = "LB", _("Label Back")


class Size(UserContentModel):
    name = models.FloatField(verbose_name=_("Size"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique size",
            )
        ]

    def __str__(self):
        return str(number_format(self.name, use_l10n=True))


class Grape(UserContentModel):
    name = models.CharField(max_length=100, verbose_name=_("Grape"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique grape",
            )
        ]

    def __str__(self):
        if self.name:
            return self.name
        return ""


class Region(UserContentModel):
    name = models.CharField(max_length=100, verbose_name=_("Region"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique region",
            )
        ]

    def __str__(self):
        return self.name


class Appellation(UserContentModel):
    name = models.CharField(max_length=100, verbose_name=_("Appellation"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique appellation",
            )
        ]

    def __str__(self):
        return self.name


class Vineyard(UserContentModel):
    name = models.CharField(max_length=100)
    website = models.CharField(max_length=100, null=True)
    region = models.CharField(max_length=250, null=True)
    country = models.CharField(
        max_length=3,
        null=True,
        choices={country.alpha_2: country.name for country in pycountry.countries},
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "country", "region", "user"],
                name="unique vineyard",
            )
        ]

    def __str__(self):
        return self.name


class FoodPairing(UserContentModel):
    name = models.CharField(max_length=100, verbose_name=_("Food"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique food pairing",
            )
        ]

    def __str__(self):
        return self.name


class Attribute(UserContentModel):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique attributes",
            )
        ]

    def __str__(self):
        return self.name


class Source(UserContentModel):
    name = models.CharField(max_length=250)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"],
                name="unique source",
            )
        ]

    def __str__(self):
        return self.name


class Wine(UserContentModel):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    wine_type = models.CharField(max_length=2, choices=WineType)
    category = models.CharField(max_length=2, choices=Category, null=True)
    grapes = models.ManyToManyField(Grape)
    attributes = models.ManyToManyField(Attribute)
    food_pairings = models.ManyToManyField(FoodPairing)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True)
    country = models.CharField(
        max_length=3,
        choices={country.alpha_2: country.name for country in pycountry.countries},
    )
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    appellation = models.ForeignKey(Appellation, on_delete=models.SET_NULL, null=True)
    location = models.JSONField(max_length=500, null=True, blank=True)
    vineyard = models.ManyToManyField(Vineyard)
    source = models.ManyToManyField(Source)

    def get_absolute_url(self):
        return reverse("wine-detail", kwargs={"pk": self.pk})

    @cached_property
    def latest_vintage(self):
        prefetched = getattr(self, "_prefetched_vintages", None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None
        return self.vintages.order_by("-year").first()

    @cached_property
    def get_vineyards(self):
        return "\n".join([str(vineyard) for vineyard in self.vineyard.all()])

    @cached_property
    def get_grapes(self):
        return ", ".join([str(grape) for grape in self.grapes.all()])

    @cached_property
    def get_sources(self):
        return ", ".join([str(s) for s in self.source.all()])

    @cached_property
    def get_attributes(self):
        return "\n".join([str(attribute) for attribute in self.attributes.all()])

    @cached_property
    def get_food_pairings(self):
        return "\n".join([str(pairing) for pairing in self.food_pairings.all()])

    @property
    def get_type(self):
        return WineType(self.wine_type).label

    @property
    def get_category(self):
        if self.category:
            return Category(self.category).label

    @cached_property
    def get_abv_range(self):
        aggregate = self.vintages.aggregate(
            min_abv=models.Min("abv"), max_abv=models.Max("abv")
        )
        min_abv, max_abv = aggregate["min_abv"], aggregate["max_abv"]
        if min_abv is None:
            return None
        if min_abv == max_abv:
            return f"{number_format(min_abv, use_l10n=True)}%"
        return (
            f"{number_format(min_abv, use_l10n=True)}"
            f"–{number_format(max_abv, use_l10n=True)}%"
        )

    @cached_property
    def get_average_rating(self):
        avg_rating = self.vintages.exclude(rating__isnull=True).aggregate(
            avg_rating=models.Avg("rating")
        )["avg_rating"]
        if avg_rating is None:
            return None
        return f"{avg_rating:.1f}/10"

    @cached_property
    def get_average_price_with_currency(self):
        # Unweighted average, across vintages, of each vintage's own average
        # price (Vintage.get_average_price_with_currency: every bottle's
        # purchase price plus the vintage's own reference price, all known
        # prices rather than just currently-stocked bottles) - not one
        # average over every stock row, so a vintage with many bottles
        # doesn't outweigh one with few.
        user_settings = get_user_settings(self.user)
        currency = settings.CURRENCY_SYMBOLS.get(
            getattr(user_settings, "currency", "EUR"), "€"
        )
        rows = self.vintages.annotate(
            price_sum=models.Sum("storageitem__price"),
            price_count=models.Count("storageitem__price"),
        ).values_list("price_sum", "price_count", "price")

        per_vintage_avgs = []
        for price_sum, price_count, vintage_price in rows:
            total = price_sum or Decimal("0")
            count = price_count or 0
            if vintage_price is not None:
                total += vintage_price
                count += 1
            if count:
                per_vintage_avgs.append(total / count)

        if not per_vintage_avgs:
            return None
        avg_price = (sum(per_vintage_avgs) / len(per_vintage_avgs)).quantize(
            Decimal("0.00")
        )
        formatted_price = number_format(avg_price, use_l10n=True)
        return f"{formatted_price}{currency}"

    @cached_property
    def total_stock(self):
        # Prefer the annotation added by WineListView.get_queryset() to avoid
        # a per-row COUNT query; fall back to a live count when unannotated
        # (e.g. wine_detail.html, which doesn't go through that queryset).
        # Cached since wine_detail.html now reads this more than once per
        # request (Stock header, stock table, and the Numbers group).
        annotated = getattr(self, "total_stock_count", None)
        if annotated is not None:
            return annotated
        from wine_cellar.apps.storage.models import StorageItem

        return StorageItem.objects.filter(vintage__wine=self, deleted=False).count()

    @property
    def get_stock(self):
        from wine_cellar.apps.storage.models import StorageItem

        return (
            StorageItem.objects.filter(vintage__wine=self, deleted=False)
            .select_related("storage", "vintage")
            .order_by("storage", "row", "column")
        )

    @property
    def image(self):
        v = self.latest_vintage
        if v:
            return v.image
        return static("images/bottle.svg")

    @property
    def image_thumbnail(self):
        v = self.latest_vintage
        if v:
            return v.image_thumbnail
        return static("images/bottle.svg")

    @property
    def image_thumbnails(self):
        v = self.latest_vintage
        if v:
            return v.image_thumbnails
        return []

    @property
    def image_urls(self):
        v = self.latest_vintage
        if v:
            return v.image_urls
        return []

    @property
    def country_name(self):
        return pycountry.countries.get(alpha_2=self.country).name

    @property
    def country_icon(self):
        return pycountry.countries.get(alpha_2=self.country).flag

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "wine_type", "size", "country", "user"],
                name="unique wine",
            )
        ]


class Vintage(UserContentModel):
    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name="vintages")
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900)],
        null=True,
        blank=True,
    )
    abv = models.FloatField(null=True, blank=True)
    barcode = models.CharField(max_length=100, null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    drink_by = models.DateField(blank=True, null=True)
    comment = models.CharField(max_length=250, blank=True)
    rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )

    def __str__(self):
        return f"{self.wine.name} {self.year or _('N/V')}"

    @property
    def drink_by_warning_date(self):
        return date.today() + timedelta(days=30)

    @property
    def get_price_with_currency(self):
        user_settings = get_user_settings(self.user)
        currency = settings.CURRENCY_SYMBOLS.get(
            getattr(user_settings, "currency", "EUR"), "€"
        )
        formatted_price = number_format(self.price, use_l10n=True)
        return f"{formatted_price}{currency}"

    @cached_property
    def get_average_price_with_currency(self):
        # Every bottle's purchase price plus the vintage's own reference
        # price (`self.price`), not just bottles currently in stock - a
        # vintage with no stock left (or none yet) but a known price still
        # contributes.
        user_settings = get_user_settings(self.user)
        currency = settings.CURRENCY_SYMBOLS.get(
            getattr(user_settings, "currency", "EUR"), "€"
        )
        aggregate = self.storageitem_set.aggregate(
            price_sum=models.Sum("price"), price_count=models.Count("price")
        )
        total = aggregate["price_sum"] or Decimal("0")
        count = aggregate["price_count"] or 0
        if self.price is not None:
            total += self.price
            count += 1

        if not count:
            return None
        avg_price = (total / count).quantize(Decimal("0.00"))
        formatted_price = number_format(avg_price, use_l10n=True)
        return f"{formatted_price}{currency}"

    @property
    def image(self):
        i = self.wineimage_set.first()
        if not i:
            return static("images/bottle.svg")
        return i.image.url

    @cached_property
    def image_thumbnail(self):
        # Prefer the Prefetch cache populated by WineListView.get_queryset()
        # over a fresh per-row query; falls back to a live lookup for views
        # (e.g. wine_detail.html) that don't prefetch it. hasattr, not
        # getattr(..., None): an empty prefetch result ([], falsy but real)
        # must not be mistaken for "wasn't prefetched at all".
        if hasattr(self, "_prefetched_front_images"):
            front = (
                self._prefetched_front_images[0]
                if self._prefetched_front_images
                else None
            )
        else:
            front = self.wineimage_set.filter(image_type=ImageType.FRONT).first()
        if not front:
            return static("images/bottle.svg")
        if front.thumbnail:
            return front.thumbnail.url
        # return normal image as fallback
        return front.image.url

    _IMAGE_ORDER = [
        ImageType.FRONT,
        ImageType.BACK,
        ImageType.LABEL_FRONT,
        ImageType.LABEL_BACK,
    ]

    @cached_property
    def _images_by_type(self):
        # Shared by image_thumbnails/image_urls so they don't each issue
        # their own wineimage_set.all() query for the same rows.
        return {img.image_type: img for img in self.wineimage_set.all()}

    @cached_property
    def image_thumbnails(self):
        result = []
        for image_type in self._IMAGE_ORDER:
            image = self._images_by_type.get(image_type)
            if image:
                src = image.thumbnail.url if image.thumbnail else image.image.url
                result.append(src)
        return result

    @cached_property
    def image_urls(self):
        # Full-size counterpart to image_thumbnails, same order/filtering -
        # lets the carousel resolve a full-size URL per index without
        # guessing one from a thumbnail filename.
        return [
            self._images_by_type[image_type].image.url
            for image_type in self._IMAGE_ORDER
            if image_type in self._images_by_type
        ]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["wine", "year", "user"],
                name="unique vintage",
            )
        ]


class WineImage(models.Model):
    image = models.ImageField(upload_to=user_directory_path)
    thumbnail = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    vintage = models.ForeignKey(Vintage, on_delete=models.CASCADE)
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    image_type = models.CharField(
        max_length=3, choices=ImageType, default=ImageType.FRONT
    )
