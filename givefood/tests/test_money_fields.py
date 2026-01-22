"""Tests for MoneyField implementation on Order and OrderLine models."""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import patch

from djmoney.money import Money
from givefood.models import Foodbank, Order, OrderLine
from givefood.const.general import DEFAULT_CURRENCY


@pytest.mark.django_db
class TestMoneyFieldConstants:
    """Test that currency constants are properly defined."""

    def test_default_currency_is_gbp(self):
        """Test that the default currency constant is GBP."""
        assert DEFAULT_CURRENCY == 'GBP'


@pytest.mark.django_db  
class TestOrderMoneyFields:
    """Test MoneyField on Order model."""

    def _create_foodbank(self):
        """Create a test foodbank."""
        foodbank = Foodbank(
            name="Test Food Bank Money",
            slug="test-food-bank-money",
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

    @patch('givefood.models.gemini')
    def test_order_cost_is_money_field(self, mock_gemini):
        """Test that Order.cost is a Money object."""
        mock_gemini.return_value = []
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        # Cost should be a Money object
        assert hasattr(order.cost, 'amount')
        assert hasattr(order.cost, 'currency')
        assert str(order.cost.currency) == 'GBP'

    @patch('givefood.models.gemini')
    def test_order_cost_default_is_zero(self, mock_gemini):
        """Test that Order.cost defaults to £0.00."""
        mock_gemini.return_value = []
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        assert order.cost.amount == Decimal('0')

    @patch('givefood.models.gemini')
    def test_order_natural_cost_returns_float(self, mock_gemini):
        """Test that natural_cost returns a float value."""
        mock_gemini.return_value = []
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        result = order.natural_cost()
        assert isinstance(result, float)
        assert result == 0.0

    @patch('givefood.models.gemini')
    def test_order_actual_cost_can_be_null(self, mock_gemini):
        """Test that Order.actual_cost can be null."""
        mock_gemini.return_value = []
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        assert order.actual_cost is None

    @patch('givefood.models.gemini')
    def test_order_natural_actual_cost_returns_none_when_null(self, mock_gemini):
        """Test that natural_actual_cost returns None when actual_cost is null."""
        mock_gemini.return_value = []
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="Test items",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        result = order.natural_actual_cost()
        assert result is None

    @patch('givefood.models.gemini')
    def test_order_cost_calculated_from_order_lines(self, mock_gemini):
        """Test that Order.cost is calculated correctly from order lines."""
        # Mock gemini to return order lines with costs in pence
        mock_gemini.return_value = [
            {"name": "Baked Beans", "quantity": 2, "item_cost": 100, "weight": 400},  # 100 pence = £1.00 per item
            {"name": "Pasta", "quantity": 1, "item_cost": 150, "weight": 500},  # 150 pence = £1.50 per item
        ]
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="2x Baked Beans, 1x Pasta",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        # Total should be: (2 * 100) + (1 * 150) = 350 pence = £3.50
        assert order.cost.amount == Decimal('3.50')
        assert order.natural_cost() == 3.50


@pytest.mark.django_db
class TestOrderLineMoneyFields:
    """Test MoneyField on OrderLine model."""

    def _create_foodbank(self):
        """Create a test foodbank."""
        foodbank = Foodbank(
            name="Test Food Bank OrderLine",
            slug="test-food-bank-orderline", 
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

    @patch('givefood.models.gemini')
    def test_orderline_costs_are_money_fields(self, mock_gemini):
        """Test that OrderLine cost fields are Money objects."""
        mock_gemini.return_value = [
            {"name": "Rice", "quantity": 3, "item_cost": 200, "weight": 1000},  # 200 pence = £2.00 per item
        ]
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="3x Rice",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        # Get the order lines
        order_lines = OrderLine.objects.filter(order=order)
        assert order_lines.count() == 1
        
        line = order_lines.first()
        
        # item_cost should be Money object: 200 pence = £2.00
        assert hasattr(line.item_cost, 'amount')
        assert line.item_cost.amount == Decimal('2.00')
        assert str(line.item_cost.currency) == 'GBP'
        
        # line_cost should be Money object: 3 * 200 pence = 600 pence = £6.00
        assert hasattr(line.line_cost, 'amount')
        assert line.line_cost.amount == Decimal('6.00')
        assert str(line.line_cost.currency) == 'GBP'

    @patch('givefood.models.gemini')
    def test_orderline_natural_cost_returns_float(self, mock_gemini):
        """Test that OrderLine.natural_cost returns a float value."""
        mock_gemini.return_value = [
            {"name": "Soup", "quantity": 1, "item_cost": 85, "weight": 400},  # 85 pence = £0.85
        ]
        
        foodbank = self._create_foodbank()
        
        order = Order(
            foodbank=foodbank,
            items_text="1x Soup",
            delivery_date=date.today(),
            delivery_hour=10,
        )
        order.save(do_foodbank_save=False)
        
        order_lines = OrderLine.objects.filter(order=order)
        line = order_lines.first()
        
        result = line.natural_cost()
        assert isinstance(result, float)
        assert result == 0.85


@pytest.mark.django_db
class TestFoodbankTotalCost:
    """Test Foodbank.total_cost with MoneyField."""

    def _create_foodbank(self):
        """Create a test foodbank."""
        foodbank = Foodbank(
            name="Test Food Bank Total Cost",
            slug="test-food-bank-total-cost",
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

    def test_total_cost_returns_zero_when_no_orders(self):
        """Test that Foodbank.total_cost returns 0 when no orders exist."""
        foodbank = self._create_foodbank()
        
        result = foodbank.total_cost()
        assert result == 0

    @patch('givefood.models.gemini')
    def test_total_cost_sums_order_costs(self, mock_gemini):
        """Test that Foodbank.total_cost correctly sums order costs."""
        mock_gemini.return_value = [
            {"name": "Item 1", "quantity": 1, "item_cost": 100, "weight": 200},
            {"name": "Item 2", "quantity": 2, "item_cost": 200, "weight": 400},
        ]
        
        foodbank = self._create_foodbank()
        
        # Create first order: 100 + (2*200) = 500 pence = £5.00
        order1 = Order(
            foodbank=foodbank,
            items_text="Test items 1",
            delivery_date=date.today(),
            delivery_hour=10,
            delivery_provider="Tesco",
        )
        order1.save(do_foodbank_save=False)
        
        # Create second order with same items: £5.00
        mock_gemini.return_value = [
            {"name": "Item 3", "quantity": 1, "item_cost": 300, "weight": 300},
        ]
        order2 = Order(
            foodbank=foodbank,
            items_text="Test items 2",
            delivery_date=date.today(),
            delivery_hour=11,
            delivery_provider="Sainsbury's",
        )
        order2.save(do_foodbank_save=False)
        
        # Total should be £5.00 + £3.00 = £8.00
        result = foodbank.total_cost()
        assert result == 8.0
