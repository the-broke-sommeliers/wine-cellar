"""Create one Vintage per existing Wine, copying its vintage-scalar fields
across, then repoint WineImage/StorageItem rows at that Vintage.

Wines that will collide under the narrower `unique wine` constraint added by
0021 (name, wine_type, size, country, user - previously `abv`/`vintage` were
also part of the key, so what used to be several Wine rows for different
vintages/abvs of the same wine) are folded onto one canonical Wine per group
(the lowest-pk row); the rest of that group's Wine rows become extra
Vintages under the canonical one and are then deleted. WineImage/
StorageItem/StorageItemEvent belonging to a folded-away Wine are repointed
at the canonical Wine first, so no history is lost.

Two wines in the same group can share a vintage year - that can't become
two Vintages of one canonical wine (Vintage's own (wine, year, user)
constraint), so folding can't just merge them. Rather than aborting the
whole migration over one conflict, the fold is resolved per year: within a
same-year cluster the oldest (lowest-pk) wine keeps the fold and any newer
wine in that cluster is excluded from it, left as its own standalone Wine
with its own single Vintage instead of being merged/deleted.

The base grouping key alone can still lump together wines that merely share
a name/type/size/country/user but aren't really the same wine, so each
candidate is also compared against the group's canonical wine on four
secondary fields: region and appellation (single-valued FKs, scored 1.0 on
a matching id or 0.0 otherwise) and vineyard and grapes (many-valued,
scored by Jaccard similarity of their related ids). A field is skipped
rather than scored when neither wine has any data for it - no data on
either side carries no signal either way. A candidate folds in only if the
average of its comparable fields' scores is >= 0.5; if none of the four
fields were comparable at all (both wines blank across the board), that
counts as a pass. A candidate that fails this check is excluded from the
fold exactly like a year collision excludes it - left as its own standalone
Wine with its own single Vintage - and, like a year-collision exclusion, it
doesn't consume a spot in `claimed_years`.

Reversible only when every wine still has exactly one vintage - see
reverse_migrate_vintage_data. The reverse copies fields back onto Wine and
deletes the Vintage rows; this is safe only because the fields it writes
back onto Wine (and the `wine` FKs on WineImage/StorageItem) are still
present at this point in the migration history - the later cleanup
migrations that remove them are unapplied first.
"""

from collections import defaultdict

from django.db import migrations, models, transaction


def _apply_vintage(Vintage, WineImage, StorageItem, wine, vintage_wine):
    """Create wine's Vintage attached to vintage_wine and repoint its
    images/stock to it. Returns the created Vintage."""
    vintage = Vintage.objects.create(
        wine=vintage_wine,
        user=wine.user,
        year=wine.vintage,
        abv=wine.abv,
        barcode=wine.barcode,
        price=wine.price,
        drink_by=wine.drink_by,
        comment=wine.comment,
        rating=wine.rating,
    )

    WineImage.objects.filter(wine=wine).update(wine=vintage_wine, vintage=vintage)
    StorageItem.objects.filter(wine=wine).update(wine=vintage_wine, vintage=vintage)
    return vintage


def _fk_similarity(candidate_id, canonical_id):
    """Score a single FK field: skip (return None) if both sides are
    unset, since neither wine has an opinion; otherwise 1.0 for a matching
    id and 0.0 for anything else (a mismatch, or one side set and the
    other not - the both-unset case is already handled above)."""
    if candidate_id is None and canonical_id is None:
        return None
    return 1.0 if candidate_id == canonical_id else 0.0


def _m2m_similarity(candidate_ids, canonical_ids):
    """Score a single M2M field as the Jaccard similarity of the two
    wines' related ids; skip (return None) only when neither side has any
    related objects at all."""
    candidate_ids = set(candidate_ids)
    canonical_ids = set(canonical_ids)
    if not candidate_ids and not canonical_ids:
        return None
    return len(candidate_ids & canonical_ids) / len(candidate_ids | canonical_ids)


def _is_similar_enough(candidate, canonical):
    """Secondary "same wine" check on top of the base grouping key:
    compares `candidate` against the group's `canonical` wine on
    region/appellation (FK) and vineyard/grapes (M2M). Fields where
    neither wine has data are skipped rather than counted against the
    fold. Folds only when the average of the comparable fields' scores is
    >= 0.5; with zero comparable fields (both wines blank on all four)
    this is an automatic pass, preserving existing behavior for wines that
    never populate these fields."""
    scores = [
        score
        for score in (
            _fk_similarity(candidate.region_id, canonical.region_id),
            _fk_similarity(candidate.appellation_id, canonical.appellation_id),
            _m2m_similarity(
                candidate.vineyard.values_list("id", flat=True),
                canonical.vineyard.values_list("id", flat=True),
            ),
            _m2m_similarity(
                candidate.grapes.values_list("id", flat=True),
                canonical.grapes.values_list("id", flat=True),
            ),
        )
        if score is not None
    ]
    if not scores:
        return True
    return sum(scores) / len(scores) >= 0.5


def migrate_vintage_data(apps, schema_editor):
    Wine = apps.get_model("wine", "Wine")
    Vintage = apps.get_model("wine", "Vintage")
    WineImage = apps.get_model("wine", "WineImage")
    StorageItem = apps.get_model("storage", "StorageItem")
    StorageItemEvent = apps.get_model("storage", "StorageItemEvent")

    with transaction.atomic():
        groups = defaultdict(list)
        for wine in Wine.objects.order_by("pk").iterator():
            key = (wine.name, wine.wine_type, wine.size_id, wine.country, wine.user_id)
            groups[key].append(wine)

        stale_wine_pks = []
        for wines in groups.values():
            # Oldest first: the first wine to claim a given vintage year
            # keeps it; a newer wine that later collides on that same year,
            # or doesn't look like the same wine on the secondary fields
            # below, is excluded from the fold. canonical is always the
            # oldest (lowest-pk) wine in the group - it's never itself
            # subject to either check.
            oldest_first = sorted(wines, key=lambda w: w.pk)
            canonical = oldest_first[0]
            claimed_years = set()
            folded = [canonical]
            standalone = []
            if canonical.vintage is not None:
                claimed_years.add(canonical.vintage)

            for wine in oldest_first[1:]:
                if wine.vintage is not None and wine.vintage in claimed_years:
                    standalone.append(wine)
                    continue
                if not _is_similar_enough(wine, canonical):
                    standalone.append(wine)
                    continue
                if wine.vintage is not None:
                    claimed_years.add(wine.vintage)
                folded.append(wine)

            for wine in folded:
                _apply_vintage(Vintage, WineImage, StorageItem, wine, canonical)
                if wine.pk != canonical.pk:
                    StorageItemEvent.objects.filter(wine=wine).update(wine=canonical)
                    stale_wine_pks.append(wine.pk)

            # Excluded wines aren't folded away - they keep their own row,
            # so their `wine`/StorageItemEvent.wine already point at the
            # right place; they only need their own Vintage.
            for wine in standalone:
                _apply_vintage(Vintage, WineImage, StorageItem, wine, wine)

        Wine.objects.filter(pk__in=stale_wine_pks).delete()


def reverse_migrate_vintage_data(apps, schema_editor):
    Wine = apps.get_model("wine", "Wine")
    Vintage = apps.get_model("wine", "Vintage")
    WineImage = apps.get_model("wine", "WineImage")
    StorageItem = apps.get_model("storage", "StorageItem")

    with transaction.atomic():
        multi_vintage_wine_pks = list(
            Wine.objects.annotate(vintage_count=models.Count("vintages"))
            .filter(vintage_count__gt=1)
            .values_list("pk", flat=True)
        )
        if multi_vintage_wine_pks:
            raise RuntimeError(
                "Cannot reverse 0020_migrate_vintage_data: wine(s) "
                f"{multi_vintage_wine_pks} have more than one vintage - "
                "reversing would silently discard all but one vintage's "
                "data. Manually consolidate each of those wines to a "
                "single vintage before reversing this migration."
            )

        for vintage in Vintage.objects.select_related("wine").iterator():
            wine = vintage.wine
            wine.vintage = vintage.year
            wine.abv = vintage.abv
            wine.barcode = vintage.barcode
            wine.price = vintage.price
            wine.drink_by = vintage.drink_by
            wine.comment = vintage.comment
            wine.rating = vintage.rating
            wine.save(
                update_fields=[
                    "vintage",
                    "abv",
                    "barcode",
                    "price",
                    "drink_by",
                    "comment",
                    "rating",
                ]
            )
            # Also clear `vintage`, not just repoint `wine` - both FKs are
            # CASCADE, so leaving them pointed at a vintage that's about to
            # be deleted below would take these rows down with it.
            WineImage.objects.filter(vintage=vintage).update(wine=wine, vintage=None)
            StorageItem.objects.filter(vintage=vintage).update(wine=wine, vintage=None)

        Vintage.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("wine", "0019_add_vintage_model"),
        ("storage", "0010_storageitem_vintage"),
    ]

    operations = [
        migrations.RunPython(migrate_vintage_data, reverse_migrate_vintage_data),
    ]
