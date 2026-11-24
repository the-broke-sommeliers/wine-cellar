from http import HTTPStatus

import pytest
from django.test import RequestFactory
from django.urls import reverse

from wine_cellar.apps.wine.models import WineTastingNote
from wine_cellar.apps.wine.views import WineDetailView


@pytest.mark.django_db
def test_add_tasting_note_with_vintage(client, user, wine_factory, vintage_factory):
    wine = wine_factory(user=user, _create_default_vintage=False)
    vintage = vintage_factory(wine=wine)
    other_wine = wine_factory(user=user)
    client.force_login(user)
    url = reverse("wine-tasting-note-add", kwargs={"wine_pk": wine.pk})

    response = client.get(url)
    assert response.status_code == HTTPStatus.OK
    assert list(response.context["form"].fields["vintage"].queryset) == [vintage]
    assert response.context["form"].fields["vintage"].empty_label == "Not specified"

    response = client.post(
        url,
        {
            "note": "Bright citrus and a long finish.",
            "rating": 4,
            "vintage": vintage.pk,
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    tasting_note = WineTastingNote.objects.get()
    assert response.url == reverse("wine-detail", kwargs={"pk": wine.pk})
    assert tasting_note.wine == wine
    assert tasting_note.vintage == vintage
    assert tasting_note.user == user
    assert tasting_note.rating == 4
    assert other_wine.tasting_notes.count() == 0

    request = RequestFactory().get(reverse("wine-detail", kwargs={"pk": wine.pk}))
    request.user = user
    detail_response = WineDetailView.as_view()(request, pk=wine.pk)
    assert list(detail_response.context_data["tasting_notes"]) == [tasting_note]


@pytest.mark.django_db
def test_tasting_note_can_be_unlinked_and_without_score(client, user, wine_factory):
    wine = wine_factory(user=user)
    client.force_login(user)

    response = client.post(
        reverse("wine-tasting-note-add", kwargs={"wine_pk": wine.pk}),
        {"note": "An easy-drinking bottle.", "rating": "", "vintage": ""},
    )

    assert response.status_code == HTTPStatus.FOUND
    tasting_note = WineTastingNote.objects.get()
    assert tasting_note.vintage is None
    assert tasting_note.rating is None


@pytest.mark.django_db
def test_tasting_note_rejects_vintage_from_another_wine(
    client, user, wine_factory, vintage_factory
):
    wine = wine_factory(user=user)
    other_wine = wine_factory(user=user)
    other_vintage = vintage_factory(wine=other_wine)
    client.force_login(user)

    response = client.post(
        reverse("wine-tasting-note-add", kwargs={"wine_pk": wine.pk}),
        {
            "note": "This should not be saved.",
            "rating": 4,
            "vintage": other_vintage.pk,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["vintage"]
    assert not WineTastingNote.objects.exists()


@pytest.mark.django_db
def test_tasting_note_score_cannot_exceed_five(client, user, wine_factory):
    wine = wine_factory(user=user)
    client.force_login(user)

    response = client.post(
        reverse("wine-tasting-note-add", kwargs={"wine_pk": wine.pk}),
        {"note": "Too many points.", "rating": 6, "vintage": ""},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["rating"]
    assert not WineTastingNote.objects.exists()


@pytest.mark.django_db
def test_tasting_note_cannot_be_added_to_another_users_wine(
    client, user_factory, wine_factory
):
    wine = wine_factory()
    client.force_login(user_factory())
    response = client.post(
        reverse("wine-tasting-note-add", kwargs={"wine_pk": wine.pk}),
        {"note": "Not my wine", "rating": 5, "vintage": ""},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert not WineTastingNote.objects.exists()


@pytest.mark.django_db
def test_tasting_note_delete_is_limited_to_owner(
    client, user, user_factory, wine_factory
):
    wine = wine_factory(user=user)
    tasting_note = WineTastingNote.objects.create(
        wine=wine, user=user, note="Original note", rating=3
    )
    client.force_login(user_factory())

    delete_url = reverse(
        "wine-tasting-note-delete",
        kwargs={"wine_pk": wine.pk, "pk": tasting_note.pk},
    )
    assert client.get(delete_url).status_code == HTTPStatus.NOT_FOUND
    assert client.post(delete_url).status_code == HTTPStatus.NOT_FOUND

    client.force_login(user)
    assert (
        client.post(
            f"/wine/{wine.pk}/tasting-notes/{tasting_note.pk}/edit/",
            {"note": "Changed", "rating": 5, "vintage": ""},
        ).status_code
        == HTTPStatus.NOT_FOUND
    )
    tasting_note.refresh_from_db()
    assert tasting_note.note == "Original note"
    assert client.get(delete_url).status_code == HTTPStatus.OK
    response = client.post(delete_url)
    assert response.status_code == HTTPStatus.FOUND
    assert not WineTastingNote.objects.filter(pk=tasting_note.pk).exists()
