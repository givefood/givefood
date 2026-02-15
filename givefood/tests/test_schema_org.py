"""
Tests for schema_org methods on Foodbank, FoodbankLocation,
FoodbankDonationPoint, and ParliamentaryConstituency models.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


OPENING_HOURS_SAMPLE = "Monday: 9:00 AM – 5:00 PM\nTuesday: 9:00 AM – 5:00 PM\nWednesday: 9:00 AM – 5:00 PM\nThursday: 9:00 AM – 5:00 PM\nFriday: 9:00 AM – 5:00 PM\nSaturday: Closed\nSunday: Closed"


def _make_mock_foodbank(**kwargs):
    mock = MagicMock()
    mock.slug = kwargs.get("slug", "test-foodbank")
    mock.uuid = kwargs.get("uuid", "12345678-1234-1234-1234-123456789abc")
    mock.name = kwargs.get("name", "Test")
    mock.alt_name = kwargs.get("alt_name", None)
    mock.url = kwargs.get("url", "https://example.com")
    mock.contact_email = kwargs.get("contact_email", "test@example.com")
    mock.phone_number = kwargs.get("phone_number", "01234567890")
    mock.postcode = kwargs.get("postcode", "SW1A 1AA")
    mock.country = kwargs.get("country", "England")
    mock.address = kwargs.get("address", "123 Test Street")
    mock.district = kwargs.get("district", "Westminster")
    mock.charity_number = kwargs.get("charity_number", "1234567")
    mock.network = kwargs.get("network", "Independent")
    mock.place_id = kwargs.get("place_id", None)
    mock.plus_code_global = kwargs.get("plus_code_global", None)
    mock.fsa_id = kwargs.get("fsa_id", None)
    mock.facebook_page = kwargs.get("facebook_page", None)
    mock.parliamentary_constituency_name = kwargs.get("parliamentary_constituency_name", "Cities of London and Westminster")
    mock.latt.return_value = 51.5
    mock.long.return_value = -0.1
    mock.full_name.return_value = "Test Food Bank"
    mock.latest_need_text.return_value = kwargs.get("needs", "Nothing")
    return mock


class TestFoodbankSchemaOrg:
    """Test Foodbank.schema_org method."""

    def test_has_demand_type_in_seeks(self):
        """Seeks entries should have @type: Demand."""
        mock = _make_mock_foodbank(needs="Pasta\nRice")
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        for item in result["seeks"]:
            assert item["@type"] == "Demand"
            assert "@type" in item["itemOffered"]
            assert item["itemOffered"]["@type"] == "Product"

    def test_has_place_type_in_location(self):
        """Nested location should have @type: Place."""
        mock = _make_mock_foodbank()
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        assert result["location"]["@type"] == "Place"

    def test_has_id(self):
        """Schema should include @id."""
        mock = _make_mock_foodbank()
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        assert "@id" in result
        assert "test-foodbank" in result["@id"]

    def test_has_additional_type(self):
        """Schema should include additionalType with Wikidata food bank URI."""
        mock = _make_mock_foodbank()
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        assert result["additionalType"] == "https://www.wikidata.org/wiki/Q1070824"

    def test_has_area_served(self):
        """Schema should include areaServed when constituency is available."""
        mock = _make_mock_foodbank()
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        assert "areaServed" in result
        assert result["areaServed"]["@type"] == "AdministrativeArea"
        assert result["areaServed"]["name"] == "Cities of London and Westminster"

    def test_no_area_served_without_constituency(self):
        """Schema should not include areaServed when constituency is absent."""
        mock = _make_mock_foodbank(parliamentary_constituency_name=None)
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        assert "areaServed" not in result

    def test_has_address_locality(self):
        """PostalAddress should include addressLocality from district."""
        mock = _make_mock_foodbank(district="Westminster")
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        assert result["address"]["addressLocality"] == "Westminster"

    def test_no_address_locality_without_district(self):
        """PostalAddress should not include addressLocality when district is absent."""
        mock = _make_mock_foodbank(district=None)
        from givefood.models import Foodbank
        result = Foodbank.schema_org(mock)
        assert "addressLocality" not in result["address"]

    def test_context_only_when_not_sub_property(self):
        """@context should only be present when not a sub property."""
        mock = _make_mock_foodbank()
        from givefood.models import Foodbank
        result_full = Foodbank.schema_org(mock, as_sub_property=False)
        result_sub = Foodbank.schema_org(mock, as_sub_property=True)
        assert "@context" in result_full
        assert "@context" not in result_sub

    def test_seeks_only_when_not_sub_property(self):
        """Seeks should only be present when not a sub property."""
        mock = _make_mock_foodbank(needs="Pasta\nRice")
        from givefood.models import Foodbank
        result_full = Foodbank.schema_org(mock, as_sub_property=False)
        result_sub = Foodbank.schema_org(mock, as_sub_property=True)
        assert "seeks" in result_full
        assert "seeks" not in result_sub

    def test_schema_org_str_calls_schema_org(self):
        """schema_org_str should call schema_org and return JSON."""
        mock = _make_mock_foodbank()
        mock.schema_org = MagicMock(return_value={"@type": "NGO", "name": "Test"})
        from givefood.models import Foodbank
        result = Foodbank.schema_org_str(mock)
        parsed = json.loads(result)
        assert parsed["@type"] == "NGO"


class TestFoodbankLocationSchemaOrg:
    """Test FoodbankLocation.schema_org method."""

    def _make_mock_location(self, **kwargs):
        mock = MagicMock()
        mock.slug = kwargs.get("slug", "test-location")
        mock.foodbank_slug = kwargs.get("foodbank_slug", "test-foodbank")
        mock.foodbank_network = kwargs.get("foodbank_network", "Independent")
        mock.address = kwargs.get("address", "456 Loc Street")
        mock.postcode = kwargs.get("postcode", "EC1A 1BB")
        mock.country = kwargs.get("country", "England")
        mock.district = kwargs.get("district", "Islington")
        mock.latt.return_value = 51.52
        mock.long.return_value = -0.09
        mock.full_name.return_value = "Test Location, Test Food Bank"
        mock.email_or_foodbank_email.return_value = "loc@example.com"
        mock.phone_or_foodbank_phone.return_value = "01234567890"

        # Create parent foodbank mock
        fb = _make_mock_foodbank()
        from givefood.models import Foodbank
        fb.schema_org = lambda as_sub_property=False: Foodbank.schema_org(fb, as_sub_property)
        fb.latest_need_text.return_value = kwargs.get("needs", "Nothing")
        mock.foodbank = fb
        return mock

    def test_has_demand_type_in_seeks(self):
        """Seeks entries should have @type: Demand."""
        mock = self._make_mock_location(needs="Pasta\nRice")
        from givefood.models import FoodbankLocation
        result = FoodbankLocation.schema_org(mock)
        for item in result["seeks"]:
            assert item["@type"] == "Demand"

    def test_has_place_type_in_location(self):
        """Nested location should have @type: Place."""
        mock = self._make_mock_location()
        from givefood.models import FoodbankLocation
        result = FoodbankLocation.schema_org(mock)
        assert result["location"]["@type"] == "Place"

    def test_has_id(self):
        """Schema should include @id."""
        mock = self._make_mock_location()
        from givefood.models import FoodbankLocation
        result = FoodbankLocation.schema_org(mock)
        assert "@id" in result
        assert "test-location" in result["@id"]

    def test_has_address_locality(self):
        """PostalAddress should include addressLocality from district."""
        mock = self._make_mock_location(district="Islington")
        from givefood.models import FoodbankLocation
        result = FoodbankLocation.schema_org(mock)
        assert result["address"]["addressLocality"] == "Islington"

    def test_no_address_locality_without_district(self):
        """PostalAddress should not include addressLocality when district is absent."""
        mock = self._make_mock_location(district=None)
        from givefood.models import FoodbankLocation
        result = FoodbankLocation.schema_org(mock)
        assert "addressLocality" not in result.get("address", {})

    def test_parent_organization_present(self):
        """parentOrganization should be present."""
        mock = self._make_mock_location()
        from givefood.models import FoodbankLocation
        result = FoodbankLocation.schema_org(mock)
        assert "parentOrganization" in result
        assert result["parentOrganization"]["@type"] == "NGO"


class TestFoodbankDonationPointSchemaOrg:
    """Test FoodbankDonationPoint.schema_org method."""

    def _make_mock_dp(self, **kwargs):
        mock = MagicMock()
        mock.name = kwargs.get("name", "Test Donation Point")
        mock.slug = kwargs.get("slug", "test-dp")
        mock.url = kwargs.get("url", "https://example.com/dp")
        mock.phone_number = kwargs.get("phone_number", "01234567890")
        mock.wheelchair_accessible = kwargs.get("wheelchair_accessible", True)
        mock.postcode = kwargs.get("postcode", "EC2A 1NT")
        mock.country = kwargs.get("country", "England")
        mock.address = kwargs.get("address", "789 DP Street")
        mock.district = kwargs.get("district", "Hackney")
        mock.opening_hours = kwargs.get("opening_hours", None)
        mock.latt.return_value = 51.52
        mock.long.return_value = -0.08

        fb = _make_mock_foodbank()
        from givefood.models import Foodbank
        fb.schema_org = lambda as_sub_property=False: Foodbank.schema_org(fb, as_sub_property)
        fb.latest_need_text.return_value = kwargs.get("needs", "Nothing")
        mock.foodbank = fb
        return mock

    def test_has_demand_type_in_seeks(self):
        """Seeks entries should have @type: Demand."""
        mock = self._make_mock_dp(needs="Pasta\nRice")
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        for item in result["seeks"]:
            assert item["@type"] == "Demand"

    def test_has_place_type_in_location(self):
        """Nested location should have @type: Place."""
        mock = self._make_mock_dp()
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        assert result["location"]["@type"] == "Place"

    def test_has_parent_organization(self):
        """Schema should include parentOrganization referencing food bank."""
        mock = self._make_mock_dp()
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        assert "parentOrganization" in result
        assert result["parentOrganization"]["@type"] == "NGO"

    def test_has_address_locality(self):
        """PostalAddress should include addressLocality from district."""
        mock = self._make_mock_dp(district="Hackney")
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        assert result["address"]["addressLocality"] == "Hackney"

    def test_no_address_locality_without_district(self):
        """PostalAddress should not include addressLocality when district is absent."""
        mock = self._make_mock_dp(district=None)
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        assert "addressLocality" not in result["address"]

    def test_opening_hours_specification(self):
        """Schema should include openingHoursSpecification when hours are available."""
        mock = self._make_mock_dp(opening_hours=OPENING_HOURS_SAMPLE)
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        assert "openingHoursSpecification" in result
        specs = result["openingHoursSpecification"]
        # Mon-Fri open, Sat-Sun closed = 5 specs
        assert len(specs) == 5
        for spec in specs:
            assert spec["@type"] == "OpeningHoursSpecification"
            assert "opens" in spec
            assert "closes" in spec
            assert "dayOfWeek" in spec

    def test_opening_hours_24h_format(self):
        """Opening hours should be in 24h format."""
        mock = self._make_mock_dp(opening_hours=OPENING_HOURS_SAMPLE)
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        spec = result["openingHoursSpecification"][0]
        assert spec["opens"] == "09:00"
        assert spec["closes"] == "17:00"

    def test_no_opening_hours_without_data(self):
        """Schema should not include openingHoursSpecification when no hours."""
        mock = self._make_mock_dp(opening_hours=None)
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        assert "openingHoursSpecification" not in result

    def test_opening_hours_skips_closed_days(self):
        """Closed days should not appear in openingHoursSpecification."""
        mock = self._make_mock_dp(opening_hours=OPENING_HOURS_SAMPLE)
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        day_urls = [s["dayOfWeek"] for s in result["openingHoursSpecification"]]
        assert "https://schema.org/Saturday" not in day_urls
        assert "https://schema.org/Sunday" not in day_urls

    def test_opening_hours_with_hyphen_separator(self):
        """Opening hours with regular hyphen separator should parse correctly."""
        hours = "Monday: 9:00 AM - 5:00 PM\nTuesday: Closed\nWednesday: Closed\nThursday: Closed\nFriday: Closed\nSaturday: Closed\nSunday: Closed"
        mock = self._make_mock_dp(opening_hours=hours)
        from givefood.models import FoodbankDonationPoint
        result = FoodbankDonationPoint.schema_org(mock)
        assert len(result["openingHoursSpecification"]) == 1
        assert result["openingHoursSpecification"][0]["opens"] == "09:00"


class TestParliamentaryConstituencySchemaOrg:
    """Test ParliamentaryConstituency.schema_org method."""

    def test_same_as_url_encodes_special_characters(self):
        """sameAs URL should properly encode special characters."""
        mock = MagicMock()
        mock.name = "Ynys Môn"
        from givefood.models import ParliamentaryConstituency
        # Mock the database queries to return empty lists
        mock.foodbank_obj.return_value = []
        mock.location_obj.return_value = []
        result = ParliamentaryConstituency.schema_org(mock)
        same_as = result["sameAs"]
        # The ô should be URL encoded
        assert "Ynys_M" in same_as
        assert " " not in same_as

    def test_same_as_url_encodes_apostrophes(self):
        """sameAs URL should properly encode apostrophes."""
        mock = MagicMock()
        mock.name = "Bishop's Stortford"
        mock.foodbank_obj.return_value = []
        mock.location_obj.return_value = []
        from givefood.models import ParliamentaryConstituency
        result = ParliamentaryConstituency.schema_org(mock)
        same_as = result["sameAs"]
        assert "'" not in same_as

    def test_schema_has_context(self):
        """Schema should include @context."""
        mock = MagicMock()
        mock.name = "Test Constituency"
        mock.foodbank_obj.return_value = []
        mock.location_obj.return_value = []
        from givefood.models import ParliamentaryConstituency
        result = ParliamentaryConstituency.schema_org(mock)
        assert result["@context"] == "https://schema.org"
        assert result["@type"] == "AdministrativeArea"
