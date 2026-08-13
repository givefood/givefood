"""Tests for the field order of the admin forms built with fields = "__all__"."""
import pytest

from givefood.forms import (
    FOODBANK_DONATION_POINT_FIELD_ORDER,
    FOODBANK_FIELD_ORDER,
    FOODBANK_LOCATION_FIELD_ORDER,
    FoodbankDonationPointForm,
    FoodbankForm,
    FoodbankLocationForm,
    FoodbankLocationPoliticsForm,
    FoodbankPoliticsForm,
)


# Foodbank, FoodbankLocation and FoodbankDonationPoint inherit their address and location fields
# from the PhysicalPlace abstract base, which sorts those fields ahead of the ones declared on the
# model itself. A fields = "__all__" form follows the model, so without an explicit field_order
# every one of these forms opens with address, postcode, lat_lng and place_id.
ORDERED_FORMS = [
    (FoodbankForm, FOODBANK_FIELD_ORDER),
    (FoodbankPoliticsForm, FOODBANK_FIELD_ORDER),
    (FoodbankLocationPoliticsForm, FOODBANK_FIELD_ORDER),
    (FoodbankLocationForm, FOODBANK_LOCATION_FIELD_ORDER),
    (FoodbankDonationPointForm, FOODBANK_DONATION_POINT_FIELD_ORDER),
]


class TestFormFieldOrder:
    """Test that the forms keep the field order they declare."""

    @pytest.mark.parametrize("form_class,field_order", ORDERED_FORMS)
    def test_form_opens_in_the_declared_order(self, form_class, field_order):
        """Test that the declared fields come first, in order, ahead of any later additions."""
        fields = list(form_class().fields.keys())
        assert fields[:len(field_order)] == field_order

    @pytest.mark.parametrize("form_class,field_order", ORDERED_FORMS)
    def test_declared_order_covers_every_field(self, form_class, field_order):
        """Test that the order lists haven't fallen behind the models they order."""
        assert set(form_class().fields.keys()) == set(field_order)

    def test_donation_point_form_starts_with_the_donation_point(self):
        """Test that the donation point form opens with its name, not its inherited address."""
        fields = list(FoodbankDonationPointForm().fields.keys())
        assert fields[:4] == ["foodbank", "name", "address", "postcode"]
        assert fields[-2:] == ["lat_lng", "place_id"]
