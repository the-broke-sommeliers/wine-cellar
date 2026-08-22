"""Tests for wine/0020_migrate_vintage_data.py, the data migration that
folds pre-existing Wine rows into Wine + Vintage. Driven via
django-test-migrations' `migrator` fixture against real historical schema
states (not the head models used elsewhere in this suite).

The `migrator` fixture pulls in pytest-django's `transactional_db`, and a
`TransactionTestCase`-style test gets its tables *flushed* (not rolled
back) at teardown - which wipes reference data seeded by earlier data
migrations (e.g. wine/0002_add_common_sizes.py's common bottle sizes).
`serialized_rollback` only restores that at the *start* of the next
serialized_rollback test's setup, not at this test's own teardown - and
since these are the only `transaction=True` tests in the suite,
pytest-django's test ordering (transactional tests always run last) means
there's never a "next" test to trigger that restore, so it would silently
leave the shared `--reuse-db` sqlite file's reference data wiped for good.
`_restore_reference_data` below explicitly reseeds it once, after every
test in this module has finished, sidestepping that gap directly instead
of relying on serialized_rollback here."""

import importlib
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

fold_migration = importlib.import_module(
    "wine_cellar.apps.wine.migrations.0020_migrate_vintage_data"
)

pytestmark = pytest.mark.django_db(transaction=True)

# Mirrors wine/0002_add_common_sizes.py's seed list.
_COMMON_SIZES = [0.1875, 0.375, 0.5, 0.75, 1.0, 1.5, 3.0, 4.5]


@pytest.fixture(scope="module", autouse=True)
def _restore_reference_data(django_db_blocker):
    yield
    with django_db_blocker.unblock():
        from wine_cellar.apps.wine.models import Size

        for size in _COMMON_SIZES:
            Size.objects.get_or_create(name=size)


PRE_STATE = [
    ("wine", "0019_add_vintage_model"),
    ("storage", "0010_storageitem_vintage"),
]
# After 0020 runs but before wine/0021 strips Wine's scalar fields and
# WineImage/StorageItem's `wine` FK - the state 0020's own reverse
# function depends on those still being present.
MID_STATE = [
    ("wine", "0020_migrate_vintage_data"),
    ("storage", "0012_storageitemevent_vintage"),
]
HEAD_STATE = [
    ("wine", "0021_cleanup_wine_vintage_fields"),
    ("storage", "0013_alter_storageitemevent_event_type"),
]
# Right where 0020 forward leaves off, before storage/0011 drops
# StorageItem.wine - the state 0020's own reverse function is documented to
# depend on. MID_STATE above deliberately advances storage further (to
# exercise StorageItemEvent, which needs storage/0012); the reverse test
# below touches StorageItem.wine directly, so it needs this earlier
# checkpoint instead.
MID_STATE_FOR_REVERSE = [
    ("wine", "0020_migrate_vintage_data"),
    ("storage", "0010_storageitem_vintage"),
]


def _create_storage(apps, user):
    Storage = apps.get_model("storage", "Storage")
    return Storage.objects.create(user=user, name="Cellar", location="Basement")


def _wine_kwargs(user, **overrides):
    return {
        "name": "Bordeaux Merlot",
        "wine_type": "RE",
        "country": "FR",
        "user": user,
        **overrides,
    }


def test_fold_collapses_duplicate_wine_and_repoints_children(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Size = old_state.apps.get_model("wine", "Size")
    WineImage = old_state.apps.get_model("wine", "WineImage")
    StorageItem = old_state.apps.get_model("storage", "StorageItem")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    size = Size.objects.create(name=750)
    common = dict(
        name="Bordeaux Merlot", wine_type="RE", country="FR", size=size, user=user
    )
    canonical_wine = Wine.objects.create(**common, vintage=2019, abv=13.0)
    other_wine = Wine.objects.create(**common, vintage=2021, abv=14.0)

    storage = _create_storage(old_state.apps, user)
    image = WineImage.objects.create(image="label.jpg", wine=other_wine)
    item = StorageItem.objects.create(storage=storage, wine=other_wine)

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")
    WineImage2 = mid_state.apps.get_model("wine", "WineImage")
    StorageItem2 = mid_state.apps.get_model("storage", "StorageItem")

    assert not Wine2.objects.filter(pk=other_wine.pk).exists()
    canonical = Wine2.objects.get(pk=canonical_wine.pk)
    vintages = {v.year: v for v in Vintage2.objects.filter(wine=canonical)}
    assert set(vintages) == {2019, 2021}
    assert vintages[2019].abv == 13.0
    assert vintages[2021].abv == 14.0

    other_vintage = vintages[2021]
    image2 = WineImage2.objects.get(pk=image.pk)
    assert image2.wine_id == canonical.pk
    assert image2.vintage_id == other_vintage.pk
    # StorageItem.wine is already dropped by storage/0011 at this point in
    # the migration chain - only `vintage` survives to check here.
    item2 = StorageItem2.objects.get(pk=item.pk)
    assert item2.vintage_id == other_vintage.pk

    # unique wine constraint (added by 0021) now holds for a genuine
    # duplicate - only meaningful with a non-null `size`, since SQL UNIQUE
    # treats every NULL as distinct from every other NULL.
    head_state = migrator.apply_tested_migration(HEAD_STATE)
    Wine3 = head_state.apps.get_model("wine", "Wine")
    Size3 = head_state.apps.get_model("wine", "Size")
    User3 = head_state.apps.get_model("auth", "User")
    dup_user = User3.objects.get(pk=user.pk)
    dup_size = Size3.objects.get(pk=size.pk)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Wine3.objects.create(
                name="Bordeaux Merlot",
                wine_type="RE",
                country="FR",
                size=dup_size,
                user=dup_user,
            )


def test_year_collision_keeps_oldest_and_excludes_newer_as_standalone(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    WineImage = old_state.apps.get_model("wine", "WineImage")
    StorageItem = old_state.apps.get_model("storage", "StorageItem")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    common = dict(name="Clash", wine_type="RE", country="FR", user=user)
    oldest = Wine.objects.create(**common, vintage=2019, abv=12.0)
    middle = Wine.objects.create(**common, vintage=2021, abv=13.0)
    newest = Wine.objects.create(**common, vintage=2019, abv=12.5)

    storage = _create_storage(old_state.apps, user)
    image_on_middle = WineImage.objects.create(image="middle.jpg", wine=middle)
    item_on_middle = StorageItem.objects.create(storage=storage, wine=middle)

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")
    WineImage2 = mid_state.apps.get_model("wine", "WineImage")
    StorageItem2 = mid_state.apps.get_model("storage", "StorageItem")

    assert Wine2.objects.count() == 2
    assert not Wine2.objects.filter(pk=middle.pk).exists()

    canonical = Wine2.objects.get(pk=oldest.pk)
    canonical_years = {v.year for v in Vintage2.objects.filter(wine=canonical)}
    assert canonical_years == {2019, 2021}

    middle_vintage = Vintage2.objects.get(wine=canonical, year=2021)
    assert WineImage2.objects.get(pk=image_on_middle.pk).wine_id == canonical.pk
    assert WineImage2.objects.get(pk=image_on_middle.pk).vintage_id == middle_vintage.pk
    # StorageItem.wine is already dropped by storage/0011 at this point in
    # the migration chain - only `vintage` survives to check here.
    assert (
        StorageItem2.objects.get(pk=item_on_middle.pk).vintage_id == middle_vintage.pk
    )

    # The newer year-2019 duplicate survives on its own, not merged in.
    standalone = Wine2.objects.get(pk=newest.pk)
    standalone_vintages = list(Vintage2.objects.filter(wine=standalone))
    assert len(standalone_vintages) == 1
    assert standalone_vintages[0].year == 2019
    assert standalone_vintages[0].wine_id == standalone.pk


def test_reverse_blocks_when_wine_has_multiple_vintages(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    common = dict(name="Bordeaux Merlot", wine_type="RE", country="FR", user=user)
    canonical_wine = Wine.objects.create(
        **common, vintage=2019, abv=13.0, price=Decimal("25.00")
    )
    Wine.objects.create(**common, vintage=2021, abv=14.0)

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    vintage_count_before = Vintage2.objects.count()
    wine_before = Wine2.objects.get(pk=canonical_wine.pk)
    snapshot = (
        wine_before.vintage,
        wine_before.abv,
        wine_before.barcode,
        wine_before.price,
        wine_before.drink_by,
        wine_before.comment,
        wine_before.rating,
    )

    with pytest.raises(RuntimeError, match="more than one vintage"):
        fold_migration.reverse_migrate_vintage_data(mid_state.apps, None)

    assert Vintage2.objects.count() == vintage_count_before
    wine_after = Wine2.objects.get(pk=canonical_wine.pk)
    after = (
        wine_after.vintage,
        wine_after.abv,
        wine_after.barcode,
        wine_after.price,
        wine_after.drink_by,
        wine_after.comment,
        wine_after.rating,
    )
    assert after == snapshot


def test_wines_for_different_users_are_not_folded_together(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    User = old_state.apps.get_model("auth", "User")

    user_a = User.objects.create(username="alice")
    user_b = User.objects.create(username="bob")
    wine_a = Wine.objects.create(**_wine_kwargs(user_a, vintage=2019, abv=13.0))
    wine_b = Wine.objects.create(**_wine_kwargs(user_b, vintage=2019, abv=13.0))

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # Same name/type/country/vintage, different owner - each keeps its own
    # row and its own single vintage, never folded across the user boundary.
    assert Wine2.objects.count() == 2
    for wine in (wine_a, wine_b):
        survivor = Wine2.objects.get(pk=wine.pk)
        vintages = list(Vintage2.objects.filter(wine=survivor))
        assert len(vintages) == 1
        assert vintages[0].wine_id == survivor.pk


def test_wines_with_different_size_are_not_folded_together(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Size = old_state.apps.get_model("wine", "Size")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    size = Size.objects.create(name=750)
    sized = Wine.objects.create(**_wine_kwargs(user, vintage=2019, size=size))
    unsized = Wine.objects.create(**_wine_kwargs(user, vintage=2019, size=None))

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # Otherwise-identical wines with different size (including no size at
    # all) belong to different fold groups.
    assert Wine2.objects.count() == 2
    for wine in (sized, unsized):
        survivor = Wine2.objects.get(pk=wine.pk)
        vintages = list(Vintage2.objects.filter(wine=survivor))
        assert len(vintages) == 1
        assert vintages[0].wine_id == survivor.pk


def test_non_vintage_wines_fold_without_false_collision(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    first = Wine.objects.create(**_wine_kwargs(user, vintage=None, abv=12.0))
    second = Wine.objects.create(**_wine_kwargs(user, vintage=None, abv=12.5))

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # `None` never counts as a "claimed" year, so two non-vintage wines
    # fold together into two year=None Vintages under one wine - relying
    # on `unique vintage` (wine, year, user) treating NULL as distinct
    # from NULL, not raising IntegrityError.
    assert Wine2.objects.count() == 1
    assert not Wine2.objects.filter(pk=second.pk).exists()
    canonical = Wine2.objects.get(pk=first.pk)

    vintages = list(Vintage2.objects.filter(wine=canonical))
    assert len(vintages) == 2
    assert {v.year for v in vintages} == {None}
    assert {v.abv for v in vintages} == {12.0, 12.5}


def test_three_way_same_year_collision_excluded_wines_stay_independent(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    oldest = Wine.objects.create(**_wine_kwargs(user, vintage=2019, abv=12.0))
    middle = Wine.objects.create(**_wine_kwargs(user, vintage=2019, abv=12.5))
    newest = Wine.objects.create(**_wine_kwargs(user, vintage=2019, abv=13.0))

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # Only the oldest wine claims 2019 and keeps the fold; the other two
    # both collide on it, so both stand alone - and independently of each
    # other, not merged together.
    assert Wine2.objects.count() == 3
    canonical = Wine2.objects.get(pk=oldest.pk)
    canonical_vintages = list(Vintage2.objects.filter(wine=canonical))
    assert len(canonical_vintages) == 1
    assert canonical_vintages[0].year == 2019

    for standalone in (middle, newest):
        survivor = Wine2.objects.get(pk=standalone.pk)
        vintages = list(Vintage2.objects.filter(wine=survivor))
        assert len(vintages) == 1
        assert vintages[0].year == 2019
        assert vintages[0].wine_id == survivor.pk


def test_dissimilar_vineyard_excludes_wine_from_fold(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Vineyard = old_state.apps.get_model("wine", "Vineyard")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    vineyard_a = Vineyard.objects.create(name="Chateau A", user=user)
    vineyard_b = Vineyard.objects.create(name="Chateau B", user=user)

    first = Wine.objects.create(**_wine_kwargs(user, vintage=2019))
    second = Wine.objects.create(**_wine_kwargs(user, vintage=2021))
    first.vineyard.set([vineyard_a])
    second.vineyard.set([vineyard_b])

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # No overlap between the two vineyards -> Jaccard score 0.0 on the only
    # comparable field -> below the 0.5 threshold -> not folded.
    assert Wine2.objects.count() == 2
    for wine in (first, second):
        survivor = Wine2.objects.get(pk=wine.pk)
        vintages = list(Vintage2.objects.filter(wine=survivor))
        assert len(vintages) == 1
        assert vintages[0].wine_id == survivor.pk


def test_matching_vineyard_and_region_still_fold_together(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Vineyard = old_state.apps.get_model("wine", "Vineyard")
    Region = old_state.apps.get_model("wine", "Region")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    vineyard = Vineyard.objects.create(name="Chateau A", user=user)
    region = Region.objects.create(name="Bordeaux", user=user)

    canonical_wine = Wine.objects.create(
        **_wine_kwargs(user, vintage=2019, region=region)
    )
    other_wine = Wine.objects.create(**_wine_kwargs(user, vintage=2021, region=region))
    canonical_wine.vineyard.set([vineyard])
    other_wine.vineyard.set([vineyard])

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # region (1.0) and vineyard (1.0, full overlap) both agree; appellation
    # and grapes are blank on both sides and skipped - average of the two
    # comparable fields is 1.0, well above the threshold, so this genuine
    # duplicate still folds exactly as it did before the similarity check
    # existed.
    assert Wine2.objects.count() == 1
    canonical = Wine2.objects.get(pk=canonical_wine.pk)
    vintages = {v.year for v in Vintage2.objects.filter(wine=canonical)}
    assert vintages == {2019, 2021}


def test_secondary_score_exactly_at_threshold_folds(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Vineyard = old_state.apps.get_model("wine", "Vineyard")
    Region = old_state.apps.get_model("wine", "Region")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    region = Region.objects.create(name="Bordeaux", user=user)
    vineyard_a = Vineyard.objects.create(name="Chateau A", user=user)
    vineyard_b = Vineyard.objects.create(name="Chateau B", user=user)

    canonical_wine = Wine.objects.create(
        **_wine_kwargs(user, vintage=2019, region=region)
    )
    other_wine = Wine.objects.create(**_wine_kwargs(user, vintage=2021, region=region))
    canonical_wine.vineyard.set([vineyard_a])
    other_wine.vineyard.set([vineyard_b])

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # Two comparable fields: region agrees (1.0), vineyard is fully
    # disjoint (0.0). appellation/grapes are blank on both sides and
    # skipped. Average = 0.5 exactly - the threshold is inclusive, so this
    # still folds.
    assert Wine2.objects.count() == 1
    canonical = Wine2.objects.get(pk=canonical_wine.pk)
    vintages = {v.year for v in Vintage2.objects.filter(wine=canonical)}
    assert vintages == {2019, 2021}


def test_secondary_score_below_threshold_excludes_wine(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Vineyard = old_state.apps.get_model("wine", "Vineyard")
    Region = old_state.apps.get_model("wine", "Region")
    Appellation = old_state.apps.get_model("wine", "Appellation")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    region = Region.objects.create(name="Bordeaux", user=user)
    appellation_a = Appellation.objects.create(name="Margaux", user=user)
    appellation_b = Appellation.objects.create(name="Pauillac", user=user)
    vineyard_a = Vineyard.objects.create(name="Chateau A", user=user)
    vineyard_b = Vineyard.objects.create(name="Chateau B", user=user)

    canonical_wine = Wine.objects.create(
        **_wine_kwargs(user, vintage=2019, region=region, appellation=appellation_a)
    )
    other_wine = Wine.objects.create(
        **_wine_kwargs(user, vintage=2021, region=region, appellation=appellation_b)
    )
    canonical_wine.vineyard.set([vineyard_a])
    other_wine.vineyard.set([vineyard_b])

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # Three comparable fields: region agrees (1.0), appellation disagrees
    # (0.0), vineyard is disjoint (0.0). grapes is blank on both sides and
    # skipped. Average = 1/3 ~= 0.33, below the threshold - excluded.
    assert Wine2.objects.count() == 2
    for wine in (canonical_wine, other_wine):
        survivor = Wine2.objects.get(pk=wine.pk)
        vintages = list(Vintage2.objects.filter(wine=survivor))
        assert len(vintages) == 1
        assert vintages[0].wine_id == survivor.pk


def test_similarity_pass_but_year_collision_still_excludes_wine(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Region = old_state.apps.get_model("wine", "Region")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    region = Region.objects.create(name="Bordeaux", user=user)

    oldest = Wine.objects.create(**_wine_kwargs(user, vintage=2019, region=region))
    newest = Wine.objects.create(**_wine_kwargs(user, vintage=2019, region=region))

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # region matches (the only comparable field) -> similarity score 1.0,
    # well above threshold - but both wines claim the same 2019 vintage
    # year, and the oldest already holds it, so the year-collision gate
    # still excludes `newest` regardless of how similar it looks. Proves
    # the two gates are independent and both must pass.
    assert Wine2.objects.count() == 2
    canonical = Wine2.objects.get(pk=oldest.pk)
    assert {v.year for v in Vintage2.objects.filter(wine=canonical)} == {2019}

    standalone = Wine2.objects.get(pk=newest.pk)
    standalone_vintages = list(Vintage2.objects.filter(wine=standalone))
    assert len(standalone_vintages) == 1
    assert standalone_vintages[0].year == 2019
    assert standalone_vintages[0].wine_id == standalone.pk


def test_similarity_excluded_wine_does_not_block_later_year_claim(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    Region = old_state.apps.get_model("wine", "Region")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    region_a = Region.objects.create(name="Bordeaux", user=user)
    region_b = Region.objects.create(name="Burgundy", user=user)

    # oldest is canonical (region A, year 2019).
    # middle shares the group's base key but has region B (mismatched
    # against canonical's region A - the only comparable field, score 0.0)
    # and claims year 2021 - it must be excluded on similarity, and its
    # year must NOT end up in claimed_years.
    # newest also claims year 2021, but matches canonical's region A - if
    # middle's exclusion had wrongly claimed 2021 anyway, this would be
    # incorrectly excluded on a phantom year collision instead of folding.
    oldest = Wine.objects.create(**_wine_kwargs(user, vintage=2019, region=region_a))
    middle = Wine.objects.create(**_wine_kwargs(user, vintage=2021, region=region_b))
    newest = Wine.objects.create(**_wine_kwargs(user, vintage=2021, region=region_a))

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # canonical (oldest) absorbs newest's 2021 vintage; middle stands alone
    # -> two surviving Wine rows total.
    assert Wine2.objects.count() == 2
    assert not Wine2.objects.filter(pk=newest.pk).exists()

    canonical = Wine2.objects.get(pk=oldest.pk)
    canonical_years = {v.year for v in Vintage2.objects.filter(wine=canonical)}
    assert canonical_years == {2019, 2021}

    standalone = Wine2.objects.get(pk=middle.pk)
    standalone_vintages = list(Vintage2.objects.filter(wine=standalone))
    assert len(standalone_vintages) == 1
    assert standalone_vintages[0].year == 2021
    assert standalone_vintages[0].wine_id == standalone.pk


def test_canonical_wines_own_children_repoint_to_its_new_vintage(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    WineImage = old_state.apps.get_model("wine", "WineImage")
    StorageItem = old_state.apps.get_model("storage", "StorageItem")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    canonical_wine = Wine.objects.create(**_wine_kwargs(user, vintage=2019, abv=12.0))
    Wine.objects.create(**_wine_kwargs(user, vintage=2021, abv=13.0))

    # Attach children to the canonical (lowest-pk) wine itself, not the
    # wine being folded away - every existing test only covers the latter.
    storage = _create_storage(old_state.apps, user)
    image = WineImage.objects.create(image="label.jpg", wine=canonical_wine)
    item = StorageItem.objects.create(storage=storage, wine=canonical_wine)

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")
    WineImage2 = mid_state.apps.get_model("wine", "WineImage")
    StorageItem2 = mid_state.apps.get_model("storage", "StorageItem")

    canonical = Wine2.objects.get(pk=canonical_wine.pk)
    own_vintage = Vintage2.objects.get(wine=canonical, year=2019)

    image2 = WineImage2.objects.get(pk=image.pk)
    assert image2.wine_id == canonical.pk
    assert image2.vintage_id == own_vintage.pk
    item2 = StorageItem2.objects.get(pk=item.pk)
    assert item2.vintage_id == own_vintage.pk


def test_storage_item_event_repoints_to_canonical_on_fold(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    StorageItemEvent = old_state.apps.get_model("storage", "StorageItemEvent")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    canonical_wine = Wine.objects.create(**_wine_kwargs(user, vintage=2019))
    other_wine = Wine.objects.create(**_wine_kwargs(user, vintage=2021))

    event = StorageItemEvent.objects.create(
        user=user, wine=other_wine, wine_name=other_wine.name, event_type="added"
    )

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    StorageItemEvent2 = mid_state.apps.get_model("storage", "StorageItemEvent")

    canonical = Wine2.objects.get(pk=canonical_wine.pk)
    event2 = StorageItemEvent2.objects.get(pk=event.pk)
    assert event2.wine_id == canonical.pk
    # wine_name/event_type are the immutable history snapshot - untouched.
    assert event2.wine_name == other_wine.name
    assert event2.event_type == "added"
    # The migration only repoints `wine`, not `vintage`, on events - not
    # asserting this as a requirement, just documenting current behavior.
    assert event2.vintage_id is None


def test_solo_wine_with_null_scalar_fields_gets_matching_vintage(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    wine = Wine.objects.create(
        **_wine_kwargs(
            user,
            vintage=None,
            abv=None,
            barcode=None,
            price=None,
            drink_by=None,
            comment="",
            rating=None,
        )
    )

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    # A lone wine with no group-mates is never "stale" - it survives, and
    # its all-null scalar fields copy across without error.
    assert Wine2.objects.filter(pk=wine.pk).exists()
    vintages = list(Vintage2.objects.filter(wine__pk=wine.pk))
    assert len(vintages) == 1
    vintage = vintages[0]
    assert vintage.year is None
    assert vintage.abv is None
    assert vintage.barcode is None
    assert vintage.price is None
    assert vintage.drink_by is None
    assert vintage.comment == ""
    assert vintage.rating is None


def test_independent_fold_groups_do_not_cross_contaminate(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    # Interleaved pks across the two groups, so the per-group oldest-first
    # sort has to actually pick each group's own lowest pk, not just the
    # global creation order.
    a_old = Wine.objects.create(**_wine_kwargs(user, name="Wine A", vintage=2018))
    b_old = Wine.objects.create(**_wine_kwargs(user, name="Wine B", vintage=2018))
    a_new = Wine.objects.create(**_wine_kwargs(user, name="Wine A", vintage=2020))
    b_new = Wine.objects.create(**_wine_kwargs(user, name="Wine B", vintage=2020))

    mid_state = migrator.apply_tested_migration(MID_STATE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")

    assert Wine2.objects.count() == 2
    assert not Wine2.objects.filter(pk=a_new.pk).exists()
    assert not Wine2.objects.filter(pk=b_new.pk).exists()

    canonical_a = Wine2.objects.get(pk=a_old.pk)
    canonical_b = Wine2.objects.get(pk=b_old.pk)
    a_vintages = list(Vintage2.objects.filter(wine=canonical_a))
    b_vintages = list(Vintage2.objects.filter(wine=canonical_b))
    assert {v.year for v in a_vintages} == {2018, 2020}
    assert {v.year for v in b_vintages} == {2018, 2020}
    # Exactly 2 each - no vintage from one wine's fold leaked into the
    # other's group.
    assert len(a_vintages) == 2
    assert len(b_vintages) == 2


def test_reverse_restores_wine_fields_and_repoints_children(migrator):
    old_state = migrator.apply_initial_migration(PRE_STATE)
    Wine = old_state.apps.get_model("wine", "Wine")
    WineImage = old_state.apps.get_model("wine", "WineImage")
    StorageItem = old_state.apps.get_model("storage", "StorageItem")
    User = old_state.apps.get_model("auth", "User")

    user = User.objects.create(username="tester")
    wine = Wine.objects.create(
        **_wine_kwargs(
            user,
            vintage=2019,
            abv=13.5,
            barcode="1234567890123",
            price=Decimal("19.99"),
            comment="Great vintage",
            rating=8,
        )
    )
    storage = _create_storage(old_state.apps, user)
    image = WineImage.objects.create(image="label.jpg", wine=wine)
    item = StorageItem.objects.create(storage=storage, wine=wine)

    # MID_STATE_FOR_REVERSE, not MID_STATE: StorageItem.wine (which the
    # reverse function writes back to) is already dropped by storage/0011
    # by the time MID_STATE's storage target is reached.
    mid_state = migrator.apply_tested_migration(MID_STATE_FOR_REVERSE)
    Wine2 = mid_state.apps.get_model("wine", "Wine")
    Vintage2 = mid_state.apps.get_model("wine", "Vintage")
    WineImage2 = mid_state.apps.get_model("wine", "WineImage")
    StorageItem2 = mid_state.apps.get_model("storage", "StorageItem")

    vintage = Vintage2.objects.get(wine__pk=wine.pk)
    assert WineImage2.objects.get(pk=image.pk).vintage_id == vintage.pk
    assert StorageItem2.objects.get(pk=item.pk).vintage_id == vintage.pk

    # A single vintage per wine satisfies the reverse guard - this is the
    # actual data-restoration path, not the RuntimeError block tested above.
    fold_migration.reverse_migrate_vintage_data(mid_state.apps, None)

    assert Vintage2.objects.count() == 0
    restored = Wine2.objects.get(pk=wine.pk)
    assert restored.vintage == 2019
    assert restored.abv == 13.5
    assert restored.barcode == "1234567890123"
    assert restored.price == Decimal("19.99")
    assert restored.comment == "Great vintage"
    assert restored.rating == 8

    # Repointed back to the wine itself - and still exist at all, proving
    # the CASCADE-on-delete-of-Vintage bug (clearing `vintage` before the
    # final `Vintage.objects.all().delete()`) is actually fixed.
    assert WineImage2.objects.get(pk=image.pk).wine_id == wine.pk
    assert StorageItem2.objects.get(pk=item.pk).wine_id == wine.pk

    # Clean up the now-`vintage=None` rows before this fixture's teardown
    # re-migrates to head - later migrations (storage/0011, wine/0021) make
    # that column NOT NULL, which existing NULL rows would violate.
    WineImage2.objects.filter(pk=image.pk).delete()
    StorageItem2.objects.filter(pk=item.pk).delete()
