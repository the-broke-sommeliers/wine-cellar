from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed

from wine_cellar.apps.storage.models import (
    StorageItem,
    StorageItemEvent,
    StorageItemEventType,
)
from wine_cellar.apps.wine.models import Size, Vintage, Wine


@pytest.mark.django_db
def test_wine_detail_authenticated(
    client, user, wine_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    client.force_login(user)
    with django_assert_num_queries(23):
        r = client.get(reverse("wine-detail", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    assertTemplateUsed(response=r, template_name="wine_detail.html")


@pytest.mark.django_db
def test_wine_detail_unauthenticated(
    client, user, wine_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    with django_assert_num_queries(1):
        r = client.get(reverse("wine-detail", kwargs={"pk": wine.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("wine-detail", kwargs={"pk": wine.pk}),
    )


@pytest.mark.django_db
def test_wine_detail_other_user_returns_404(
    client, user, user_factory, wine_factory, django_assert_num_queries
):
    other_user = user_factory()
    wine = wine_factory(user=other_user)
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.get(reverse("wine-detail", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_wine_detail_with_location_renders_map_tag(
    client, user, wine_factory, geojson_point_dict, django_assert_num_queries
):
    """`{% react_detail_map wine %}` is only rendered when `wine.location`
    is set - assert that branch actually runs, not just the no-location
    default path every other detail-view test exercises."""
    wine = wine_factory(user=user, location=geojson_point_dict)
    client.force_login(user)
    with django_assert_num_queries(23):
        r = client.get(reverse("wine-detail", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    assert 'id="wine_map"' in r.content.decode()


@pytest.mark.django_db
def test_wine_update_other_user_returns_404(
    client, user, user_factory, wine_factory, django_assert_num_queries
):
    other_user = user_factory()
    wine = wine_factory(user=other_user)
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.get(reverse("wine-edit", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_wine_update_post_other_user_returns_404(
    client, user, user_factory, wine_factory, django_assert_num_queries
):
    other_user = user_factory()
    wine = wine_factory(user=other_user)
    client.force_login(user)
    size = Size.objects.get(name=0.75)
    data = {
        "name": "Hacked",
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "year": 2002,
        "country": "DE",
    }
    with django_assert_num_queries(3):
        r = client.post(reverse("wine-edit", kwargs={"pk": wine.pk}), data)
    assert r.status_code == HTTPStatus.NOT_FOUND
    wine.refresh_from_db()
    assert wine.name != "Hacked"


@pytest.mark.django_db
def test_wine_update_nonexistent_pk_returns_404(
    client, user, django_assert_num_queries
):
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.get(reverse("wine-edit", kwargs={"pk": 999999}))
    assert r.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_wine_update_duplicate(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    size = Size.objects.get(name=0.75)
    wine1 = wine_factory(
        user=user,
        name="Merlot",
        wine_type="RE",
        size=size,
        country="DE",
        _create_default_vintage=False,
    )
    vintage_factory(wine=wine1, year=2002, abv=13.0)
    wine2 = wine_factory(
        user=user,
        name="Chardonnay",
        wine_type="WH",
        size=size,
        country="FR",
        _create_default_vintage=False,
    )
    vintage_factory(wine=wine2, year=2020, abv=12.0)
    client.force_login(user)
    data = {
        "name": wine1.name,
        "wine_type": wine1.wine_type,
        "category": "DR",
        "abv": wine1.latest_vintage.abv,
        "size": size.pk,
        "year": wine1.latest_vintage.year,
        "country": wine1.country,
    }
    with django_assert_num_queries(25):
        r = client.post(reverse("wine-edit", kwargs={"pk": wine2.pk}), data)
    assert r.status_code == HTTPStatus.OK
    assert r.context_data["form"].errors
    wine2.refresh_from_db()
    assert wine2.name == "Chardonnay"


@pytest.mark.django_db
def test_wine_edit_shows_vintage_scoping_hint_only_for_multi_vintage_wines(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    single = wine_factory(user=user)
    client.force_login(user)
    with django_assert_num_queries(20):
        r = client.get(reverse("wine-edit", kwargs={"pk": single.pk}))
    assert r.status_code == HTTPStatus.OK
    assert "apply only to the" not in r.content.decode()

    multi = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=multi, year=2019)
    vintage_factory(wine=multi, year=2021)
    with django_assert_num_queries(20):
        r = client.get(reverse("wine-edit", kwargs={"pk": multi.pk}))
    assert r.status_code == HTTPStatus.OK
    assert "apply only to the 2021 vintage" in r.content.decode()


@pytest.mark.django_db
def test_wine_update_valid_fields(
    client,
    user,
    wine,
    grape_factory,
    food_pairing_factory,
    source_factory,
    attribute_factory,
    vineyard_factory,
    django_assert_num_queries,
):
    grape1 = grape_factory()
    grape_factory()
    food_pairing = food_pairing_factory()
    source = source_factory()
    vineyard = vineyard_factory()
    attribute = attribute_factory()
    size = Size.objects.get(name=0.75)
    client.force_login(user)
    data = {
        "name": wine.name,
        "wine_type": "RE",
        "category": "DR",
        "abv": 13.0,
        "size": size.pk,
        "year": 2002,
        "grapes": grape1.pk,
        "food_pairings": food_pairing.pk,
        "source": source.pk,
        "vineyard": vineyard.pk,
        "attributes": attribute.pk,
        "country": "DE",
    }
    with django_assert_num_queries(55):
        r = client.post(reverse("wine-edit", kwargs={"pk": wine.pk}), data, follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="wine_detail.html")
    changed_wine = Wine.objects.first()
    assert changed_wine.name == wine.name
    assert changed_wine.wine_type == data["wine_type"]
    assert changed_wine.latest_vintage.abv == data["abv"]
    assert changed_wine.size == size
    assert changed_wine.latest_vintage.year == data["year"]
    assert changed_wine.grapes.count() == 1
    assert changed_wine.grapes.first() == grape1
    assert changed_wine.food_pairings.count() == 1
    assert changed_wine.food_pairings.first() == food_pairing
    assert changed_wine.vineyard.count() == 1
    assert changed_wine.vineyard.first() == vineyard
    assert changed_wine.source.count() == 1
    assert changed_wine.source.first() == source
    assert changed_wine.attributes.count() == 1


@pytest.mark.django_db
def test_wine_delete(client, user, wine_factory, django_assert_num_queries):
    wine = wine_factory(user=user)
    client.force_login(user)
    with django_assert_num_queries(30):
        r = client.post(reverse("wine-delete", kwargs={"pk": wine.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(response=r, expected_url=reverse("wine-list"))
    assert not Wine.objects.exists()


@pytest.mark.django_db
def test_wine_delete_logs_removed_event(
    client, user, wine_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    client.force_login(user)
    with django_assert_num_queries(20):
        client.post(reverse("wine-delete", kwargs={"pk": wine.pk}))
    event = StorageItemEvent.objects.get(event_type=StorageItemEventType.WINE_REMOVED)
    assert event.wine_name == wine.name
    # The wine itself is gone, so its FK is nulled out - only the name lives on.
    assert event.wine is None


@pytest.mark.django_db
def test_wine_delete_preserves_bottle_history(
    client, user, wine_factory, storage_item_factory, django_assert_num_queries
):
    """A bottle's history must survive the cascade delete of its wine."""
    wine = wine_factory(user=user, name="Chablis 2019")
    item = storage_item_factory(
        storage__user=user, vintage=wine.latest_vintage, user=user
    )
    client.force_login(user)
    with django_assert_num_queries(9):
        client.post(
            reverse("stock-open", kwargs={"pk": item.pk}), data={"note": "party"}
        )

    events_before = StorageItemEvent.objects.filter(wine_name=wine.name).count()
    assert events_before == 1  # the OPENED event

    with django_assert_num_queries(23):
        client.post(reverse("wine-delete", kwargs={"pk": wine.pk}))

    assert not Wine.objects.exists()
    assert not StorageItem.objects.exists()
    events = StorageItemEvent.objects.filter(wine_name=wine.name).order_by("created")
    assert [e.event_type for e in events] == [
        StorageItemEventType.OPENED,
        StorageItemEventType.REMOVED,
        StorageItemEventType.WINE_REMOVED,
    ]
    opened_event = events[0]
    assert opened_event.storage_item is None
    assert opened_event.wine is None
    assert opened_event.wine_name == "Chablis 2019"
    assert opened_event.note == "party"


@pytest.mark.django_db
def test_wine_delete_logs_removed_event_for_active_bottles(
    client, user, wine_factory, storage_item_factory, django_assert_num_queries
):
    """Every still-active bottle gets its own REMOVED event on wine delete."""
    wine = wine_factory(user=user)
    storage_item_factory(storage__user=user, vintage=wine.latest_vintage, user=user)
    storage_item_factory(
        storage__user=user, vintage=wine.latest_vintage, user=user, opened=True
    )
    already_consumed = storage_item_factory(
        storage__user=user,
        vintage=wine.latest_vintage,
        user=user,
        opened=True,
        deleted=True,
    )
    consumed_event = StorageItemEvent.objects.create(
        storage_item=already_consumed,
        wine=wine,
        wine_name=wine.name,
        user=user,
        event_type=StorageItemEventType.CONSUMED,
    )
    client.force_login(user)

    with django_assert_num_queries(23):
        client.post(reverse("wine-delete", kwargs={"pk": wine.pk}))

    removed_events = StorageItemEvent.objects.filter(
        wine_name=wine.name, event_type=StorageItemEventType.REMOVED
    )
    # Only the two still-active bottles, not the already-consumed one.
    assert removed_events.count() == 2
    for event in removed_events:
        assert event.note == "Removed automatically because the wine was deleted."
        assert event.storage_item is None

    consumed_event.refresh_from_db()
    assert consumed_event.event_type == StorageItemEventType.CONSUMED


@pytest.mark.django_db
def test_wine_delete_other_user_returns_404(
    client, user, user_factory, wine_factory, django_assert_num_queries
):
    other_user = user_factory()
    wine = wine_factory(user=other_user)
    client.force_login(user)
    with django_assert_num_queries(3):
        r = client.post(reverse("wine-delete", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert Wine.objects.count() == 1


@pytest.mark.django_db
def test_vintage_delete_last_vintage_is_blocked(
    client, user, wine_factory, django_assert_num_queries
):
    wine = wine_factory(user=user)
    vintage = wine.latest_vintage
    client.force_login(user)
    r = client.post(
        reverse("vintage-delete", kwargs={"wine_pk": wine.pk, "pk": vintage.pk})
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert Vintage.objects.filter(pk=vintage.pk).exists()


@pytest.mark.django_db
def test_vintage_delete_with_no_stock_logs_only_the_summary_event(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    keep = vintage_factory(wine=wine, year=2019)
    to_delete = vintage_factory(wine=wine, year=2021)
    client.force_login(user)
    r = client.post(
        reverse("vintage-delete", kwargs={"wine_pk": wine.pk, "pk": to_delete.pk}),
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert not Vintage.objects.filter(pk=to_delete.pk).exists()
    assert Vintage.objects.filter(pk=keep.pk).exists()
    events = StorageItemEvent.objects.filter(wine_name=wine.name)
    assert [e.event_type for e in events] == [StorageItemEventType.VINTAGE_REMOVED]
    assert events[0].vintage_year == 2021


@pytest.mark.django_db
def test_vintage_delete_logs_removed_events_for_active_bottles(
    client,
    user,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    """Deleting a non-last vintage with active stock removes that stock and
    logs a REMOVED event per bottle, plus a VINTAGE_REMOVED summary event -
    mirroring wine delete's history-preserving behaviour."""
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, year=2019)
    to_delete = vintage_factory(wine=wine, year=2021)
    active_item = storage_item_factory(storage__user=user, vintage=to_delete, user=user)
    already_consumed = storage_item_factory(
        storage__user=user, vintage=to_delete, user=user, deleted=True
    )
    client.force_login(user)

    client.post(
        reverse("vintage-delete", kwargs={"wine_pk": wine.pk, "pk": to_delete.pk})
    )

    assert not Vintage.objects.filter(pk=to_delete.pk).exists()
    assert not StorageItem.objects.filter(pk=active_item.pk).exists()
    # The already-consumed bottle cascades away too (it's still tied to the
    # deleted vintage) but must not get its own REMOVED event.
    assert not StorageItem.objects.filter(pk=already_consumed.pk).exists()
    removed_events = StorageItemEvent.objects.filter(
        wine_name=wine.name, event_type=StorageItemEventType.REMOVED
    )
    assert removed_events.count() == 1
    event = removed_events.first()
    assert event.vintage_year == 2021
    assert event.note == "Removed automatically because the vintage was deleted."
    summary_event = StorageItemEvent.objects.get(
        wine_name=wine.name, event_type=StorageItemEventType.VINTAGE_REMOVED
    )
    assert summary_event.vintage_year == 2021


@pytest.mark.django_db
def test_vintage_delete_confirm_page_warns_about_active_stock(
    client,
    user,
    wine_factory,
    vintage_factory,
    storage_item_factory,
    django_assert_num_queries,
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, year=2019)
    to_delete = vintage_factory(wine=wine, year=2021)
    storage_item_factory(storage__user=user, vintage=to_delete, user=user)
    client.force_login(user)
    r = client.get(
        reverse("vintage-delete", kwargs={"wine_pk": wine.pk, "pk": to_delete.pk})
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["active_stock_count"] == 1
    assert "still has" in r.content.decode()


@pytest.mark.django_db
def test_vintage_delete_other_user_returns_404(
    client, user, user_factory, wine_factory, django_assert_num_queries
):
    other_user = user_factory()
    wine = wine_factory(user=other_user)
    vintage = wine.latest_vintage
    client.force_login(user)
    r = client.post(
        reverse("vintage-delete", kwargs={"wine_pk": wine.pk, "pk": vintage.pk})
    )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert Vintage.objects.filter(pk=vintage.pk).exists()


@pytest.mark.django_db
def test_vintage_create_duplicate_year_shows_form_error(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, year=2020)
    client.force_login(user)
    r = client.post(reverse("vintage-add", kwargs={"wine_pk": wine.pk}), {"year": 2020})
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors["year"]
    assert Vintage.objects.filter(wine=wine).count() == 1


@pytest.mark.django_db
def test_vintage_create_same_year_different_wine_is_allowed(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine_a = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine_a, year=2020)
    wine_b = wine_factory(user=user, _create_default_vintage=False)
    client.force_login(user)
    r = client.post(
        reverse("vintage-add", kwargs={"wine_pk": wine_b.pk}),
        {"year": 2020},
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    assert Vintage.objects.filter(wine=wine_b, year=2020).exists()


@pytest.mark.django_db
def test_vintage_update_duplicate_year_shows_form_error(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage_factory(wine=wine, year=2020)
    other = vintage_factory(wine=wine, year=2021)
    client.force_login(user)
    r = client.post(
        reverse("vintage-edit", kwargs={"wine_pk": wine.pk, "pk": other.pk}),
        {"year": 2020},
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors["year"]
    other.refresh_from_db()
    assert other.year == 2021


@pytest.mark.django_db
def test_vintage_update_keeping_its_own_year_is_allowed(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    """Editing a vintage without changing its year must not false-positive
    against itself."""
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage = vintage_factory(wine=wine, year=2020, comment="")
    client.force_login(user)
    r = client.post(
        reverse("vintage-edit", kwargs={"wine_pk": wine.pk, "pk": vintage.pk}),
        {"year": 2020, "comment": "updated"},
        follow=True,
    )
    assert r.status_code == HTTPStatus.OK
    vintage.refresh_from_db()
    assert vintage.comment == "updated"


@pytest.mark.django_db
def test_wine_update_duplicate_vintage_year_shows_vintage_specific_message(
    client, user, wine_factory, vintage_factory, django_assert_num_queries
):
    """A vintage-year collision reached via the wine-edit form (which
    embeds the latest vintage's scalar fields) must report a
    vintage-specific message, not the wine-level duplicate message."""
    size = Size.objects.get(name=0.75)
    wine = wine_factory(
        user=user,
        wine_type="RE",
        size=size,
        country="DE",
        _create_default_vintage=False,
    )
    vintage_factory(wine=wine, year=2019)
    latest = vintage_factory(wine=wine, year=2021)
    client.force_login(user)
    data = {
        "name": wine.name,
        "wine_type": wine.wine_type,
        "category": "DR",
        "abv": latest.abv,
        "size": size.pk,
        "year": 2019,
        "country": wine.country,
    }
    r = client.post(reverse("wine-edit", kwargs={"pk": wine.pk}), data)
    assert r.status_code == HTTPStatus.OK
    errors = r.context_data["form"].errors
    assert "year" in errors
    assert "vintage with this year" in str(errors["year"])
    latest.refresh_from_db()
    assert latest.year == 2021
