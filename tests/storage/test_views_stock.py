import json
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse
from pytest_django.asserts import assertRedirects, assertTemplateUsed

from wine_cellar.apps.storage.models import (
    Storage,
    StorageItem,
    StorageItemEvent,
    StorageItemEventType,
)
from wine_cellar.apps.storage.views import (
    SlotConflictError,
    StorageItemAddView,
    StorageItemUpdateView,
)


@pytest.mark.django_db
def test_unauthenticated_cant_add_stock(client, user, wine_factory):
    wine = wine_factory(user=user)
    r = client.post(reverse("stock-add", kwargs={"pk": wine.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r,
        expected_url=reverse("account_login")
        + "?next="
        + reverse("stock-add", kwargs={"pk": wine.pk}),
    )
    assertTemplateUsed(response=r, template_name="base.html")
    assertTemplateUsed(response=r, template_name="account/login.html")


@pytest.mark.django_db
def test_user_can_add_stock(client, user, wine_factory):
    client.force_login(user)
    storage = Storage.objects.first()
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 1
    item = storage.items.first()
    assert item.wine == wine
    event = StorageItemEvent.objects.get(storage_item=item)
    assert event.event_type == StorageItemEventType.ADDED


@pytest.mark.django_db
def test_user_can_add_multiple_bottles_to_unlimited_shelf(client, user, wine_factory):
    client.force_login(user)
    storage = Storage.objects.first()
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "quantity": 3,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 3
    assert all(item.wine == wine for item in storage.items.all())
    assert (
        StorageItemEvent.objects.filter(
            storage_item__in=storage.items.all(), event_type=StorageItemEventType.ADDED
        ).count()
        == 3
    )


@pytest.mark.django_db
def test_user_cant_add_stock_to_other_users_storage(
    client, user, user_factory, wine_factory
):
    storage = Storage.objects.filter(user=user).first()
    other_user = user_factory()
    other_storage = Storage.objects.filter(user=other_user).first()
    client.force_login(user)
    wine = wine_factory(user=user)
    other_wine = wine_factory(user=other_user)
    data = {
        "storage": other_storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert other_storage.used_slots == 0
    r = client.post(
        reverse("stock-add", kwargs={"pk": other_wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert other_storage.used_slots == 0
    assert StorageItem.objects.count() == 0
    data = {
        "storage": storage.pk,
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": other_wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert other_storage.used_slots == 0
    assert StorageItem.objects.count() == 0


@pytest.mark.django_db
def test_user_can_delete_stock(client, user, wine_factory, storage_item_factory):
    client.force_login(user)
    storage = Storage.objects.first()
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, user=user)
    assert item.deleted is False
    assert StorageItem.objects.count() == 1
    r = client.post(reverse("stock-delete", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert StorageItem.objects.count() == 1
    item.refresh_from_db()
    assert item.deleted is True
    event = StorageItemEvent.objects.get(storage_item=item)
    assert event.event_type == StorageItemEventType.REMOVED


@pytest.mark.django_db
def test_user_cant_delete_other_users_stock(
    client, user, user_factory, wine_factory, storage_item_factory
):
    client.force_login(user)
    user2 = user_factory()
    storage = Storage.objects.filter(user=user2).first()
    wine = wine_factory(user=user2)
    item = storage_item_factory(storage=storage, wine=wine, user=user2)
    assert item.deleted is False
    assert StorageItem.objects.count() == 1
    r = client.post(reverse("stock-delete", kwargs={"pk": item.pk}), follow=True)
    assert r.status_code == HTTPStatus.NOT_FOUND
    assert StorageItem.objects.count() == 1
    item.refresh_from_db()
    assert item.deleted is False


@pytest.mark.django_db
def test_user_cant_add_to_full_slot(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=1, columns=1)
    client.force_login(user)
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[1, 1]]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    # Only the pre-existing occupant - the rejected submission created nothing.
    assert StorageItem.objects.filter(wine=wine).count() == 1


@pytest.mark.django_db
def test_add_stock_race_rechecks_under_lock(user, storage_factory, wine_factory):
    """Two requests both saw slot (1, 1) as free - the second write must be
    rejected by the lock+recheck, not double-occupy the slot."""
    storage = storage_factory(user=user, rows=1, columns=1)
    wine1 = wine_factory(user=user)
    wine2 = wine_factory(user=user)
    cleaned_data = {"storage": storage, "price": None, "slots": [(1, 1)]}

    StorageItemAddView.process_form_data(wine1, user, cleaned_data)
    assert StorageItem.objects.filter(storage=storage, deleted=False).count() == 1

    with pytest.raises(SlotConflictError):
        StorageItemAddView.process_form_data(wine2, user, cleaned_data)

    # No partial/duplicate write from the rejected second call.
    assert StorageItem.objects.filter(storage=storage, deleted=False).count() == 1
    assert StorageItem.objects.filter(wine=wine2).count() == 0


@pytest.mark.django_db
def test_user_can_add_to_specific_slot(client, user, storage_factory, wine_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[2, 1]]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    item = storage.items.first()
    assert item.wine == wine
    assert item.row == 2
    assert item.column == 1


@pytest.mark.django_db
def test_user_can_add_multiple_slots_at_once(
    client, user, storage_factory, wine_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[1, 1], [1, 2], [2, 1]]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 3
    coords = set(storage.items.values_list("row", "column"))
    assert coords == {(1, 1), (1, 2), (2, 1)}
    assert (
        StorageItemEvent.objects.filter(
            storage_item__in=storage.items.all(), event_type=StorageItemEventType.ADDED
        ).count()
        == 3
    )


@pytest.mark.django_db
def test_user_cant_add_duplicate_slot(client, user, storage_factory, wine_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[1, 1], [1, 1]]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert StorageItem.objects.count() == 0


@pytest.mark.django_db
def test_user_cant_add_with_no_slots_selected(
    client, user, storage_factory, wine_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert StorageItem.objects.count() == 0


@pytest.mark.django_db
def test_partial_over_capacity_add_creates_nothing(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    """One free slot requested alongside one that's already occupied - the
    whole submission is rejected, not partially fulfilled."""
    storage = storage_factory(user=user, rows=1, columns=2)
    client.force_login(user)
    occupant = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=occupant, row=1, column=1, user=user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[1, 1], [1, 2]]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    assert StorageItem.objects.filter(wine=wine).count() == 0


@pytest.mark.django_db
def test_user_cant_add_to_invalid_slot(client, user, storage_factory, wine_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[3, 1]]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
def test_form_context_has_grid_cells(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    r = client.get(reverse("stock-add", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    payload = r.context["storage_cells_data"][storage.pk]
    assert payload["unlimited"] is False
    assert {(c["row"], c["column"]): c["state"] for c in payload["cells"]} == {
        (1, 1): "free",
        (1, 2): "free",
        (2, 1): "free",
        (2, 2): "free",
    }
    storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    storage_item_factory(storage=storage, wine=wine, row=2, column=2, user=user)
    r = client.get(reverse("stock-add", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    payload = r.context["storage_cells_data"][storage.pk]
    assert {(c["row"], c["column"]): c["state"] for c in payload["cells"]} == {
        (1, 1): "occupied",
        (1, 2): "free",
        (2, 1): "free",
        (2, 2): "occupied",
    }


@pytest.mark.django_db
def test_form_context_marks_unlimited_shelf(client, user, wine_factory):
    client.force_login(user)
    storage = Storage.objects.filter(user=user).first()
    wine = wine_factory(user=user)
    r = client.get(reverse("stock-add", kwargs={"pk": wine.pk}))
    assert r.status_code == HTTPStatus.OK
    assert r.context["storage_cells_data"][storage.pk] == {"unlimited": True}


@pytest.mark.django_db
def test_edit_form_context_marks_current_slot(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    r = client.get(reverse("stock-edit", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.OK
    payload = r.context["storage_cells_data"][storage.pk]
    assert {(c["row"], c["column"]): c["state"] for c in payload["cells"]} == {
        (1, 1): "current",
        (1, 2): "free",
        (2, 1): "free",
        (2, 2): "free",
    }


@pytest.mark.django_db
def test_edit_form_context_only_marks_current_for_its_own_storage(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    """A different storage that happens to share the same coordinates as
    the item's current slot must not have that cell marked "current" too -
    only the storage the item actually lives in gets that treatment."""
    storage = storage_factory(user=user, rows=1, columns=1)
    other_storage = storage_factory(user=user, rows=1, columns=1)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    r = client.get(reverse("stock-edit", kwargs={"pk": item.pk}))
    assert r.status_code == HTTPStatus.OK
    other_payload = r.context["storage_cells_data"][other_storage.pk]
    assert {(c["row"], c["column"]): c["state"] for c in other_payload["cells"]} == {
        (1, 1): "free",
    }


@pytest.mark.django_db
def test_used_slot_is_free_after_delete(
    client, user, storage_factory, storage_item_factory, wine_factory
):
    wine = wine_factory(user=user)
    wine_new = wine_factory(user=user)
    storage = storage_factory(user=user, rows=2, columns=2)
    storage_item_factory(
        storage=storage, wine=wine, row=1, column=1, user=user, deleted=True
    )
    client.force_login(user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[1, 1]]),
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine_new.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine_new.pk})
    )
    item = storage.items.filter(deleted=False).first()
    assert item.wine == wine_new
    assert item.row == 1
    assert item.column == 1
    assert item.deleted is False


@pytest.mark.django_db
def test_user_can_edit_existing_item_new_slot(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[2, 1]]),
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 1
    assert storage.items.first().wine == wine
    item = storage.items.first()
    assert item.wine == wine
    assert item.row == 2
    assert item.column == 1


@pytest.mark.django_db
def test_user_can_edit_existing_item_keeping_same_slot(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    """Submitting the bottle's own current slot (the "current" cell, not
    "free") is a no-op move and must still be accepted."""
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[1, 1]]),
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    item.refresh_from_db()
    assert item.row == 1
    assert item.column == 1


@pytest.mark.django_db
def test_user_can_edit_existing_item_new_price(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(
        storage=storage, wine=wine, row=1, column=1, user=user, price=10.0
    )
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[1, 1]]),
        "price": 15.0,
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    assert storage.used_slots == 1
    assert storage.items.first().wine == wine
    item = storage.items.first()
    assert item.wine == wine
    assert item.row == 1
    assert item.column == 1
    assert item.price == 15.0


@pytest.mark.django_db
def test_user_cant_edit_to_occupied_slot(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    storage_item_factory(
        storage=storage, wine=wine_factory(user=user), row=2, column=1, user=user
    )
    data = {
        "storage": storage.pk,
        "slots": json.dumps([[2, 1]]),
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
def test_edit_stock_race_rechecks_under_lock(
    user, storage_factory, wine_factory, storage_item_factory
):
    """A slot taken between validation and write must be rejected."""
    storage = storage_factory(user=user, rows=1, columns=2)
    wine = wine_factory(user=user)
    item_to_move = storage_item_factory(
        storage=storage, wine=wine, row=1, column=1, user=user
    )
    storage_item_factory(
        storage=storage, wine=wine_factory(user=user), row=1, column=2, user=user
    )
    cleaned_data = {"storage": storage, "price": None, "slots": [(1, 2)]}

    with pytest.raises(SlotConflictError):
        StorageItemUpdateView.process_form_data(item_to_move, user, cleaned_data)

    item_to_move.refresh_from_db()
    assert (item_to_move.row, item_to_move.column) == (1, 1)


@pytest.mark.django_db
def test_user_cant_edit_grid_slot_with_no_slot_selected(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": storage.pk,
        "slots": json.dumps([]),
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    item.refresh_from_db()
    assert item.row == 1
    assert item.column == 1


@pytest.mark.django_db
def test_user_can_edit_item_to_unlimited_shelf(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    unlimited_storage = Storage.objects.filter(user=user).first()
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": unlimited_storage.pk,
        "slots": json.dumps([]),
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assertRedirects(
        response=r, expected_url=reverse("wine-detail", kwargs={"pk": wine.pk})
    )
    item.refresh_from_db()
    assert item.storage == unlimited_storage
    assert item.row is None
    assert item.column is None


@pytest.mark.django_db
def test_user_cant_edit_item_to_unlimited_shelf_with_stale_slot(
    client, user, storage_factory, wine_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    unlimited_storage = Storage.objects.filter(user=user).first()
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": unlimited_storage.pk,
        "slots": json.dumps([[1, 1]]),
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors
    item.refresh_from_db()
    assert item.storage == storage


@pytest.mark.django_db
def test_user_cant_edit_to_other_users_storage(
    client, user, user_factory, storage_factory, wine_factory, storage_item_factory
):
    other_user = user_factory()
    other_storage = Storage.objects.filter(user=other_user).first()
    storage = storage_factory(user=user, rows=2, columns=2)
    client.force_login(user)
    wine = wine_factory(user=user)
    item = storage_item_factory(storage=storage, wine=wine, row=1, column=1, user=user)
    data = {
        "storage": other_storage.pk,
    }
    r = client.post(
        reverse("stock-edit", kwargs={"pk": item.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    assert r.context["form"].errors


@pytest.mark.django_db
def test_user_can_add_stock_with_price(client, user, wine_factory):
    client.force_login(user)
    storage = Storage.objects.filter(user=user).first()
    wine = wine_factory(user=user)
    data = {
        "storage": storage.pk,
        "price": "12.50",
    }
    r = client.post(
        reverse("stock-add", kwargs={"pk": wine.pk}), data=data, follow=True
    )
    assert r.status_code == HTTPStatus.OK
    item = StorageItem.objects.filter(wine=wine).first()
    assert item is not None
    assert item.price == Decimal("12.50")
