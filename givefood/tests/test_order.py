import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from givefood.models import Foodbank, Order, OrderGroup, OrderLine


@pytest.mark.django_db
class TestOrderGroupDecaching:
    """Test that Order triggers decaching of OrderGroup public pages when saved."""

    @patch('givefood.models.decache_async')
    @patch('givefood.models.gemini')
    def test_save_with_public_order_group_triggers_decaching(self, mock_gemini, mock_decache):
        """Test that saving an order with a public OrderGroup triggers decaching."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank",
            slug="test-food-bank",
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

        # Create a public OrderGroup
        order_group = OrderGroup(
            name="Test Order Group",
            slug="test-order-group",
            public=True,
            key="testkey1"
        )
        order_group.save()

        # Create an order with the public order group
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
            order_group=order_group,
        )
        order.save(do_foodbank_save=False)

        # Verify that decache_async.enqueue was called
        assert mock_decache.enqueue.called
        # Get the URLs that were passed to decache_async.enqueue
        call_args = mock_decache.enqueue.call_args
        urls = call_args[0][0]
        
        # Verify the correct URLs were decached
        assert len(urls) == 3
        assert f"/donate/managed/{order_group.slug}-{order_group.key}/" in urls[0]
        assert f"/donate/managed/{order_group.slug}-{order_group.key}/geo.json" in urls[1]
        assert f"/donate/managed/{order_group.slug}-{order_group.key}/items/" in urls[2]

    @patch('givefood.models.decache_async')
    @patch('givefood.models.gemini')
    def test_save_with_non_public_order_group_does_not_trigger_decaching(self, mock_gemini, mock_decache):
        """Test that saving an order with a non-public OrderGroup does not trigger decaching."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 2",
            slug="test-food-bank-2",
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

        # Create a non-public OrderGroup
        order_group = OrderGroup(
            name="Test Order Group 2",
            slug="test-order-group-2",
            public=False,
            key="testkey2"
        )
        order_group.save()

        # Create an order with the non-public order group
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
            order_group=order_group,
        )
        order.save(do_foodbank_save=False)

        # Verify that decache_async.enqueue was NOT called
        assert not mock_decache.enqueue.called

    @patch('givefood.models.decache_async')
    @patch('givefood.models.gemini')
    def test_save_without_order_group_does_not_trigger_decaching(self, mock_gemini, mock_decache):
        """Test that saving an order without an OrderGroup does not trigger decaching."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank 3",
            slug="test-food-bank-3",
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

        # Create an order without an order group
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
            order_group=None,
        )
        order.save(do_foodbank_save=False)

        # Verify that decache_async.enqueue was NOT called
        assert not mock_decache.enqueue.called


@pytest.mark.django_db
class TestNullableFoodbank:
    """Test that Order can be created without a foodbank."""

    @patch('givefood.models.gemini')
    def test_order_without_foodbank(self, mock_gemini):
        """Test that an order can be created without a foodbank."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create an order without a foodbank
        order = Order(
            foodbank=None,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)

        # Verify the order was created
        assert order.id is not None
        assert order.foodbank is None
        assert order.order_id.startswith("gf-unassigned-")
        assert order.country == ""

    @patch('givefood.models.gemini')
    def test_foodbank_name_slug_with_null_foodbank(self, mock_gemini):
        """Test that foodbank_name_slug returns 'unassigned' for orders without a foodbank."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create an order without a foodbank
        order = Order(
            foodbank=None,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)

        # Verify the foodbank_name_slug method
        assert order.foodbank_name_slug() == "unassigned"

    @patch('givefood.models.gemini')
    def test_foodbank_name_slug_with_foodbank(self, mock_gemini):
        """Test that foodbank_name_slug returns the foodbank slug when foodbank is set."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank",
            slug="test-food-bank",
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

        # Create an order with a foodbank
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)

        # Verify the foodbank_name_slug method
        assert order.foodbank_name_slug() == "test-food-bank"

    @patch('givefood.models.gemini')
    def test_foodbank_deletion_unassigns_orders(self, mock_gemini):
        """Test that deleting a foodbank unassigns orders instead of deleting them."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank Delete",
            slug="test-food-bank-delete",
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

        # Create an order with the foodbank
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        order_id = order.id

        # Delete the foodbank
        foodbank.delete()

        # Verify the order still exists but is unassigned
        order = Order.objects.get(id=order_id)
        assert order.foodbank is None

    @patch('givefood.models.gemini')
    def test_order_line_unassigned_when_foodbank_deleted(self, mock_gemini):
        """Test that OrderLine.foodbank is set to None when the foodbank is deleted."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        # Create a food bank
        foodbank = Foodbank(
            name="Test Food Bank Delete Line",
            slug="test-food-bank-delete-line",
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

        # Create an order with the foodbank
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)

        # Get order lines (created by the save method)
        order_lines = OrderLine.objects.filter(order=order)
        
        # Delete the foodbank
        foodbank.delete()

        # Verify all order lines have null foodbank
        for line in order_lines:
            line.refresh_from_db()
            assert line.foodbank is None
