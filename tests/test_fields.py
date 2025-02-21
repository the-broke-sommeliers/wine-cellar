import pytest
from django.forms import forms

from wine_cellar.apps.wine.fields import OpenMultipleChoiceField
from wine_cellar.apps.wine.models import Size


class TestForm(forms.Form):
    required_field = OpenMultipleChoiceField(
        queryset=Size.objects.all(), field_name="name", required=True
    )
    non_required_field = OpenMultipleChoiceField(
        queryset=Size.objects.all(), field_name="name", required=False
    )


class TestFormSlicedQs(forms.Form):
    required_field = OpenMultipleChoiceField(
        queryset=Size.objects.all()[:5], field_name="name", required=True
    )


class TestFormType(forms.Form):
    required_field = OpenMultipleChoiceField(
        queryset=Size.objects.all(), field_name="name", required=True, field_class=float
    )


def test_open_multiple_choice_required():
    form = TestForm(data={"required_field": []})
    assert not form.is_valid()


@pytest.mark.django_db
def test_open_multiple_choice_required_present(size_factory):
    size = size_factory()
    form = TestForm(data={"required_field": [size.pk]})
    assert form.is_valid()


@pytest.mark.django_db
def test_open_multiple_choice_required_invalid(size_factory):
    size_factory()
    form = TestFormSlicedQs(data={"required_field": ["a"]})
    assert not form.is_valid()


@pytest.mark.django_db
def test_open_multiple_choice_non_required_invalid(size_factory):
    size = size_factory()
    form = TestForm(data={"required_field": [size.pk], "non_required_field": [""]})
    assert form.is_valid()


@pytest.mark.django_db
def test_open_multiple_choice_incompatible_field_class(size_factory):
    size_factory()
    form = TestFormType(data={"required_field": ["tom_new_optaaa"]})
    assert not form.is_valid()


@pytest.mark.django_db
def test_open_multiple_choice_compatible_field_class(size_factory):
    size_factory()
    form = TestFormType(data={"required_field": ["tom_new_opt1"]})
    assert form.is_valid()
