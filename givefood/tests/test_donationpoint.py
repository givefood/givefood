import pytest
from unittest.mock import patch
from givefood.models import Foodbank, FoodbankDonationPoint


@pytest.mark.django_db
class TestDonationPointDecaching:
    """Test that FoodbankDonationPoint triggers decaching of /api/3/donationpoints/ when saved."""

    @patch('givefood.models.decache_async')
    def test_save_triggers_decaching(self, mock_decache):
        """Test that saving a donation point triggers decaching of the donationpoints API prefix."""
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank DP",
            slug="test-food-bank-dp",
            address="Test Address",
            postcode="SW1A 1AA",
            country="England",
            lat_lng="51.5014,-0.1419",
            latitude=51.5014,
            longitude=-0.1419,
            network="Independent",
            url="https://test.example.com",
            shopping_list_url="https://test.example.com/shopping",
            contact_email="test@example.com",
        )
        foodbank.save(do_geoupdate=False, do_decache=False)

        # Create a donation point
        donation_point = FoodbankDonationPoint(
            foodbank=foodbank,
            name="Test Donation Point",
            address="Test DP Address",
            postcode="SW1A 1AA",
            lat_lng="51.5014,-0.1419",
        )
        donation_point.save(do_geoupdate=False, do_foodbank_resave=False, do_photo_update=False)

        # Verify that decache_async.enqueue was called with the donationpoints prefix
        assert mock_decache.enqueue.called
        call_args = mock_decache.enqueue.call_args
        prefixes = call_args[1].get("prefixes") or call_args[0][0] if call_args[0] else call_args[1].get("prefixes")
        assert "/api/3/donationpoints/" in prefixes
