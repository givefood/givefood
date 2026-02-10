import pytest
from unittest.mock import patch, Mock, MagicMock
from requests.exceptions import ReadTimeout, ConnectionError
from givefood.func import do_foodbank_need_check


class TestDoFoodbankNeedCheck:
    """Tests for the do_foodbank_need_check function"""

    def test_do_foodbank_need_check_handles_read_timeout(self):
        """
        Test that do_foodbank_need_check properly handles ReadTimeout exceptions
        and returns a proper dict instead of returning the exception object.
        
        This is a regression test for the bug where ReadTimeout was returned
        as-is, causing a TypeError when the view tried to pass it to render().
        """
        # Create a mock foodbank
        foodbank = Mock()
        foodbank.slug = "test-foodbank"
        foodbank.name = "Test Foodbank"
        foodbank.shopping_list_url = "https://example.com/needs"
        foodbank.url = "https://example.com"
        foodbank.last_need_check = None
        foodbank.save = Mock()

        # Mock the requests.get to raise ReadTimeout
        with patch('givefood.func.requests.get') as mock_get, \
             patch('givefood.func.FoodbankDiscrepancy') as mock_discrepancy, \
             patch('givefood.func.CrawlItem') as mock_crawl_item, \
             patch('givefood.func.datetime') as mock_datetime:
            
            mock_get.side_effect = ReadTimeout("Read timed out")
            mock_discrepancy_instance = Mock()
            mock_discrepancy.return_value = mock_discrepancy_instance
            mock_crawl_item_instance = Mock()
            mock_crawl_item.return_value = mock_crawl_item_instance
            mock_datetime.now.return_value = "2026-02-10"
            
            # Call the function
            result = do_foodbank_need_check(foodbank)
            
            # Verify it returns a dict (not an exception object)
            assert isinstance(result, dict), f"Expected dict but got {type(result)}"
            
            # Verify the dict has the expected keys
            assert "foodbank" in result
            assert "need_prompt" in result
            assert "is_nonpertinent" in result
            assert "is_change" in result
            assert "change_state" in result
            assert "need_text" in result
            assert "excess_text" in result
            assert "last_published_need" in result
            assert "last_nonpublished_needs" in result
            
            # Verify the values make sense for an error case
            assert result["foodbank"] == foodbank
            assert result["is_change"] == False
            assert result["need_text"] == ""
            assert result["excess_text"] == ""

    def test_do_foodbank_need_check_handles_connection_error(self):
        """
        Test that do_foodbank_need_check properly handles ConnectionError exceptions.
        """
        # Create a mock foodbank
        foodbank = Mock()
        foodbank.slug = "another-test-foodbank"
        foodbank.name = "Another Test Foodbank"
        foodbank.shopping_list_url = "https://example.com/needs"
        foodbank.url = "https://example.com"
        foodbank.last_need_check = None
        foodbank.save = Mock()

        # Mock the requests.get to raise ConnectionError
        with patch('givefood.func.requests.get') as mock_get, \
             patch('givefood.func.FoodbankDiscrepancy') as mock_discrepancy, \
             patch('givefood.func.CrawlItem') as mock_crawl_item, \
             patch('givefood.func.datetime') as mock_datetime:
            
            mock_get.side_effect = ConnectionError("Connection refused")
            mock_discrepancy_instance = Mock()
            mock_discrepancy.return_value = mock_discrepancy_instance
            mock_crawl_item_instance = Mock()
            mock_crawl_item.return_value = mock_crawl_item_instance
            mock_datetime.now.return_value = "2026-02-10"
            
            # Call the function
            result = do_foodbank_need_check(foodbank)
            
            # Verify it returns a dict (not an exception object)
            assert isinstance(result, dict), f"Expected dict but got {type(result)}"
            
            # Verify the dict has the expected keys
            assert "foodbank" in result
            assert "error" in result
