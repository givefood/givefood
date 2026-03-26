import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from givefood.models import Foodbank, FoodbankChange, FoodbankChangeLine, Order, OrderGroup, OrderLine
from givefood.const.item_types import ITEM_CATEGORY_GROUPS


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
    def test_order_line_accessible_via_order_when_foodbank_deleted(self, mock_gemini):
        """Test that OrderLine can access foodbank via order.foodbank after foodbank deletion."""
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
        
        # Verify order lines can access foodbank via order before deletion
        for line in order_lines:
            assert line.order.foodbank == foodbank
        
        # Delete the foodbank
        foodbank.delete()

        # Verify order lines can still be accessed and order.foodbank is None
        for line in order_lines:
            line.refresh_from_db()
            assert line.order.foodbank is None

    @patch('givefood.models.gemini')
    def test_multiple_unassigned_orders_allowed(self, mock_gemini):
        """Test that multiple unassigned orders with same delivery date/provider are allowed."""
        # Mock gemini to return empty list to avoid AI call
        mock_gemini.return_value = []
        
        delivery_date = date.today()
        delivery_hour = 10
        
        # Create first unassigned order
        order1 = Order(
            foodbank=None,
            items_text="Test items 1",
            delivery_date=delivery_date,
            delivery_hour=delivery_hour,
            delivery_provider="Tesco",
        )
        order1.save(do_foodbank_save=False)
        
        # Create second unassigned order with same delivery date and provider
        order2 = Order(
            foodbank=None,
            items_text="Test items 2",
            delivery_date=delivery_date,
            delivery_hour=delivery_hour,
            delivery_provider="Tesco",
        )
        order2.save(do_foodbank_save=False)
        
        # Verify both orders were created successfully
        assert order1.id is not None
        assert order2.id is not None
        assert order1.id != order2.id
        # Verify they have different order_ids (because timestamps differ)
        assert order1.order_id != order2.order_id


@pytest.mark.django_db
class TestOrderLineCategorisation:
    """Test that OrderLine.save() sets category and group."""

    def _create_foodbank(self, name="Test Food Bank", slug="test-food-bank"):
        foodbank = Foodbank(
            name=name,
            slug=slug,
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
        return foodbank

    def _create_order(self, foodbank, mock_gemini):
        mock_gemini.return_value = []
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        return order

    @patch('givefood.models.gemini')
    def test_uses_gemini_when_no_previous_categorisation(self, mock_gemini):
        """Test that Gemini is called when the item name has no previous categorisation."""
        foodbank = self._create_foodbank()
        order = self._create_order(foodbank, mock_gemini)

        mock_gemini.reset_mock()
        mock_gemini.return_value = "Pasta"

        order_line = OrderLine(
            order=order,
            name="Fusilli Pasta 500g",
            quantity=2,
            item_cost=100,
            line_cost=200,
            weight=1000,
            calories=0,
        )
        order_line.save()

        assert order_line.category == "Pasta"
        assert order_line.group == ITEM_CATEGORY_GROUPS["Pasta"]
        mock_gemini.assert_called_once()

    @patch('givefood.models.gemini')
    def test_uses_existing_foodbank_change_line_category(self, mock_gemini):
        """Test that existing FoodbankChangeLine category is used instead of Gemini."""
        foodbank = self._create_foodbank(name="Test FB Cat", slug="test-fb-cat")
        order = self._create_order(foodbank, mock_gemini)

        # Create a FoodbankChange and FoodbankChangeLine with a known category
        need = FoodbankChange(
            foodbank=foodbank,
            uri="https://test.example.com",
            change_text="Baked Beans",
            published=True,
        )
        need.save(do_translate=False, do_foodbank_save=False)
        change_line = FoodbankChangeLine(
            need=need,
            item="Baked Beans 400g",
            type="need",
            category="Baked Beans",
        )
        change_line.save()

        mock_gemini.reset_mock()

        order_line = OrderLine(
            order=order,
            name="Baked Beans 400g",
            quantity=1,
            item_cost=50,
            line_cost=50,
            weight=400,
            calories=0,
        )
        order_line.save()

        assert order_line.category == "Baked Beans"
        assert order_line.group == ITEM_CATEGORY_GROUPS["Baked Beans"]
        mock_gemini.assert_not_called()

    @patch('givefood.models.gemini')
    def test_defaults_to_other_when_gemini_returns_invalid(self, mock_gemini):
        """Test that category defaults to 'Other' when Gemini returns an invalid category."""
        foodbank = self._create_foodbank(name="Test FB Inv", slug="test-fb-inv")
        order = self._create_order(foodbank, mock_gemini)

        mock_gemini.reset_mock()
        mock_gemini.return_value = "InvalidCategory"

        order_line = OrderLine(
            order=order,
            name="Unknown Item XYZ",
            quantity=1,
            item_cost=100,
            line_cost=100,
            weight=500,
            calories=0,
        )
        order_line.save()

        assert order_line.category == "Other"
        assert order_line.group == ITEM_CATEGORY_GROUPS["Other"]

    @patch('givefood.models.gemini')
    def test_does_not_overwrite_existing_category(self, mock_gemini):
        """Test that an already-set category is not overwritten."""
        foodbank = self._create_foodbank(name="Test FB Pre", slug="test-fb-pre")
        order = self._create_order(foodbank, mock_gemini)

        mock_gemini.reset_mock()

        order_line = OrderLine(
            order=order,
            name="Some Item",
            quantity=1,
            item_cost=100,
            line_cost=100,
            weight=500,
            calories=0,
            category="Rice",
            group="Meal Food",
        )
        order_line.save()

        assert order_line.category == "Rice"
        assert order_line.group == "Meal Food"
        mock_gemini.assert_not_called()
